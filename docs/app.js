(function () {
  "use strict";

  var data = { students: [], contests: {} };
  var searchEl = document.getElementById("search");
  var resultsEl = document.getElementById("results");
  var emptyEl = document.getElementById("empty");
  var loadingEl = document.getElementById("loading");
  var hintEl = document.getElementById("search-hint");
  var contestListEl = document.getElementById("contest-list");
  var awardsRankingListEl = document.getElementById("awards-ranking-list");
  var topStudentsSectionEl = document.getElementById("top-students-section");
  var searchClearEl = document.getElementById("search-clear");
  var girlsOnlyEl = document.getElementById("girls-only");
  var gradeFilterEl = document.getElementById("grade-filter");
  var gradeFilterWrapEl = document.getElementById("grade-filter-wrap");

  function setLoading(busy) {
    loadingEl.setAttribute("aria-busy", busy ? "true" : "false");
    loadingEl.hidden = !busy;
  }

  function normalize(s) {
    return (s || "").toLowerCase().trim();
  }

  function matchStudent(student, query) {
    if (!query) return false;
    var q = normalize(query);
    if (normalize(student.name).indexOf(q) !== -1) return true;
    for (var i = 0; i < (student.aliases || []).length; i++) {
      if (normalize(student.aliases[i]).indexOf(q) !== -1) return true;
    }
    return false;
  }

  function escapeHtml(s) {
    var div = document.createElement("div");
    div.textContent = s;
    return div.innerHTML;
  }

  /**
   * Current grade based on grade_in_2026 (grade at Jan 1, 2026).
   * New school year starts Sept 1 each year.
   * Returns null if gradeIn2026 is missing or invalid.
   */
  function getCurrentGrade(gradeIn2026) {
    if (gradeIn2026 == null || gradeIn2026 === "") return null;
    var g = parseInt(String(gradeIn2026).trim(), 10);
    if (isNaN(g)) return null;
    var d = new Date();
    var y = d.getFullYear();
    var m = d.getMonth() + 1;
    var day = d.getDate();
    if (y < 2026) return g;
    var bumps = (m > 9 || (m === 9 && day >= 1)) ? (y - 2026 + 1) : (y - 2026);
    return g + bumps;
  }

  /** Returns grade label string (e.g. "G10", "U1") or "" if no grade. */
  function getGradeLabel(gradeIn2026) {
    var currentGrade = getCurrentGrade(gradeIn2026);
    if (currentGrade == null) return "";
    return currentGrade <= 12 ? "G" + currentGrade : "U" + (currentGrade - 12);
  }

  /** Sort key for grade labels: G6..G12 then U1, U2, ... */
  function gradeLabelSortKey(label) {
    if (!label || label === "") return -1;
    if (label.charAt(0) === "G") return parseInt(label.slice(1), 10);
    if (label.charAt(0) === "U") return 12 + parseInt(label.slice(1), 10);
    return -1;
  }

  function recordToDisplayKeys(record) {
    var skip = { contest: true, year: true, contest_slug: true };
    var keys = [];
    for (var k in record) {
      if (!skip[k] && Object.prototype.hasOwnProperty.call(record, k)) {
        keys.push(k);
      }
    }
    return keys.sort();
  }

  function allRecordHeaders(records) {
    var set = {};
    for (var r = 0; r < records.length; r++) {
      var keys = recordToDisplayKeys(records[r]);
      for (var i = 0; i < keys.length; i++) set[keys[i]] = true;
    }
    var arr = [];
    for (var k in set) if (Object.prototype.hasOwnProperty.call(set, k)) arr.push(k);
    return arr.sort();
  }

  function compareContestSlugs(a, b) {
    var orderMap = data && data.contest_order_map ? data.contest_order_map : null;
    if (orderMap) {
      var hasA = Object.prototype.hasOwnProperty.call(orderMap, a);
      var hasB = Object.prototype.hasOwnProperty.call(orderMap, b);
      if (hasA && hasB) return orderMap[a] - orderMap[b];
      if (hasA && !hasB) return -1;
      if (!hasA && hasB) return 1;
    }
    return a.localeCompare(b);
  }

  function renderRecordRow(record, allKeys) {
    var cells = [
      "<td class=\"num\" data-col=\"year\">", escapeHtml(record.year || ""), "</td>"
    ];
    for (var i = 0; i < allKeys.length; i++) {
      var key = allKeys[i];
      var val = record[key] != null ? record[key] : "";
      var cellClass = key === "rank" ? "num rank-" + (val === "1" || val === 1 ? "1" : (val === "2" || val === 2 || val === "3" || val === 3 ? "2" : "")) : "num";
      cells.push("<td class=\"" + cellClass + "\" data-col=\"" + escapeHtml(key) + "\">", escapeHtml(String(val)), "</td>");
    }
    return "<tr>" + cells.join("") + "</tr>";
  }

  function renderContestInfo(slug, contestsMap) {
    var c = (contestsMap || {})[slug];
    if (!c) return "";
    var parts = ["<div class=\"contest-info\">"];
    parts.push("<h3 class=\"contest-info-title\">" + escapeHtml(c.contest_name || slug) + "</h3>");
    if (c.description) {
      parts.push("<p class=\"contest-info-description\">" + escapeHtml(c.description) + "</p>");
    }
    if (c.website) {
      parts.push("<a href=\"" + escapeHtml(c.website) + "\" target=\"_blank\" rel=\"noopener noreferrer\" class=\"contest-info-website\">Visit website</a>");
    }
    parts.push("</div>");
    return parts.join("");
  }

  function groupRecordsByContest(records) {
    var bySlug = {};
    for (var i = 0; i < records.length; i++) {
      var r = records[i];
      var slug = r.contest_slug || r.contest || "other";
      if (!bySlug[slug]) bySlug[slug] = [];
      bySlug[slug].push(r);
    }
    var slugs = [];
    for (var s in bySlug) if (Object.prototype.hasOwnProperty.call(bySlug, s)) slugs.push(s);
    slugs.sort(compareContestSlugs);
    return { bySlug: bySlug, slugs: slugs };
  }

  function renderStudent(student, contestsMap) {
    var records = student.records || [];
    var grouped = groupRecordsByContest(records);
    var bySlug = grouped.bySlug;
    var slugs = grouped.slugs;
    var state = student.state || "";

    var sections = [];
    for (var i = 0; i < slugs.length; i++) {
      var slug = slugs[i];
      var contestRecords = bySlug[slug];
      contestRecords.sort(function (a, b) {
        var yA = a.year || "";
        var yB = b.year || "";
        return yA > yB ? -1 : yA < yB ? 1 : 0;
      });
      var allKeys = allRecordHeaders(contestRecords);
      var headerCells = "<th data-col=\"year\">" + escapeHtml("Year") + "</th>" + allKeys.map(function (k) {
        var label = k.replace(/_/g, " ");
        return "<th data-col=\"" + escapeHtml(k) + "\">" + escapeHtml(label) + "</th>";
      }).join("");
      var rows = contestRecords.map(function (r) { return renderRecordRow(r, allKeys); }).join("");

      sections.push(
        "<div class=\"contest-section\">" +
          renderContestInfo(slug, contestsMap) +
          "<div class=\"records-table-wrap\">" +
            "<table class=\"records-table\">" +
              "<thead><tr>" + headerCells + "</tr></thead>" +
              "<tbody>" + rows + "</tbody>" +
            "</table>" +
          "</div>" +
        "</div>"
      );
    }

    var aliasesHtml = "";
    if (student.aliases && student.aliases.length) {
      aliasesHtml = "<span class=\"student-aliases\">Also known as: " +
        student.aliases.map(function (a) { return "<span>" + escapeHtml(a) + "</span>"; }).join("") +
        "</span>";
    }

    var stateHtml = "";
    if (state) {
      stateHtml = "<span class=\"student-state\">(" + escapeHtml(String(state)) + ")</span>";
    }

    return (
      "<article class=\"student-card\" data-student-id=\"" + escapeHtml(String(student.id)) + "\">" +
        "<div class=\"student-header\">" +
          "<h2 class=\"student-name\" data-student-name=\"" + escapeHtml(String(student.name || "")) + "\">" + escapeHtml(student.name) + (stateHtml ? " " + stateHtml : "") + "</h2>" +
          aliasesHtml +
          "<button type=\"button\" class=\"export-pdf-student-btn\" aria-label=\"Export this student to PDF\">Export to PDF</button>" +
        "</div>" +
        "<div class=\"student-contests\">" + sections.join("") + "</div>" +
      "</article>"
    );
  }

  function renderContestList() {
    if (!contestListEl) return;
    var contests = data.contests || {};
    var contestYearFiles = data.contest_year_files || {};
    var yearsBySlug = {};
    var students = data.students || [];
    for (var s = 0; s < students.length; s++) {
      var recs = students[s].records || [];
      for (var r = 0; r < recs.length; r++) {
        var slug = recs[r].contest_slug;
        if (!slug) continue;
        if (!yearsBySlug[slug]) yearsBySlug[slug] = {};
        yearsBySlug[slug][recs[r].year] = true;
      }
    }
    var slugs = [];
    for (var k in contests) if (Object.prototype.hasOwnProperty.call(contests, k)) slugs.push(k);
    slugs = slugs.filter(function (slug) {
      return !slug.toLowerCase().startsWith("bmt");
    });
    slugs.sort(compareContestSlugs);
    var parts = [];
    var githubBase = "https://github.com/x-du/math-competition/blob/main/database/contests/";
    for (var i = 0; i < slugs.length; i++) {
      var slug = slugs[i];
      var c = contests[slug];
      var name = (c && c.contest_name) ? c.contest_name : slug;
      var years = [];
      if (yearsBySlug[slug]) {
        for (var y in yearsBySlug[slug]) if (Object.prototype.hasOwnProperty.call(yearsBySlug[slug], y)) years.push(y);
        years.sort(function (a, b) { return b.localeCompare(a, undefined, { numeric: true }); });
      }
      var nameHtml = (c && c.website)
        ? "<a href=\"" + escapeHtml(c.website) + "\" target=\"_blank\" rel=\"noopener noreferrer\" class=\"contest-list-link\">" + escapeHtml(name) + "</a>"
        : "<span class=\"contest-list-item\">" + escapeHtml(name) + "</span>";
      var yearLinks = [];
      var filesByYear = contestYearFiles[slug] || {};
      for (var j = 0; j < years.length; j++) {
        var yr = years[j];
        var filename = filesByYear[yr] || "results.csv";
        var yearHref = githubBase + slug + "/year%3D" + yr + "/" + filename;
        yearLinks.push("<a href=\"" + yearHref + "\" target=\"_blank\" rel=\"noopener noreferrer\" class=\"contest-list-year-link\">" + escapeHtml(yr) + "</a>");
      }
      var yearLine = yearLinks.length ? "<span class=\"contest-list-years\">" + yearLinks.join(", ") + "</span>" : "";
      parts.push("<div class=\"contest-list-block\">" + nameHtml + (yearLine ? "<br>" + yearLine : "") + "</div>");
    }
    contestListEl.innerHTML = parts.length ? parts.join("") : "";
  }

  function renderTopStudentsByRecords() {
    if (!awardsRankingListEl) return;
    var students = data.students || [];
    var withRecords = (students || []).filter(function (s) {
      var recs = s.records || [];
      return recs.length > 0;
    });

    var gradeLabelSet = {};
    var hasNoGrade = false;
    for (var i = 0; i < withRecords.length; i++) {
      var lab = getGradeLabel(withRecords[i].grade_in_2026);
      if (lab === "") hasNoGrade = true;
      else gradeLabelSet[lab] = true;
    }
    var gradeLabels = [];
    for (var k in gradeLabelSet) if (Object.prototype.hasOwnProperty.call(gradeLabelSet, k)) gradeLabels.push(k);
    gradeLabels.sort(function (a, b) {
      return gradeLabelSortKey(a) - gradeLabelSortKey(b);
    });

    if (gradeFilterEl) {
      var currentValue = gradeFilterEl.value;
      gradeFilterEl.innerHTML = "<option value=\"\">All grades</option>";
      for (var j = 0; j < gradeLabels.length; j++) {
        var opt = document.createElement("option");
        opt.value = gradeLabels[j];
        opt.textContent = gradeLabels[j];
        gradeFilterEl.appendChild(opt);
      }
      if (hasNoGrade) {
        var noneOpt = document.createElement("option");
        noneOpt.value = "__none__";
        noneOpt.textContent = "No grade";
        gradeFilterEl.appendChild(noneOpt);
      }
      if (currentValue && gradeFilterEl.querySelector("option[value=\"" + currentValue + "\"]")) {
        gradeFilterEl.value = currentValue;
      }
    }

    if (girlsOnlyEl && girlsOnlyEl.checked) {
      students = students.filter(function (s) {
        return (s.gender || "").toLowerCase() === "female";
      });
    }
    if (gradeFilterEl && gradeFilterWrapEl && !gradeFilterWrapEl.hidden && gradeFilterEl.value && gradeFilterEl.value !== "") {
      var wantLabel = gradeFilterEl.value;
      students = students.filter(function (s) {
        var lab = getGradeLabel(s.grade_in_2026);
        return wantLabel === "__none__" ? lab === "" : lab === wantLabel;
      });
    }

    var totalCountEl = document.getElementById("total-student-count");
    if (totalCountEl) totalCountEl.textContent = String(students.length);
    var counts = [];
    if (students && students.length) {
      for (var i = 0; i < students.length; i++) {
        var student = students[i];
        var records = student.records || [];
        var count = records.length;
        if (count > 0) {
          counts.push({ student: student, recordsCount: count });
        }
      }
    }

    if (!counts.length) {
      var emptyMsg = (girlsOnlyEl && girlsOnlyEl.checked)
        ? "No female students with records in this view."
        : "No record data available yet.";
      awardsRankingListEl.innerHTML = "<li class=\"awards-ranking-empty\">" + escapeHtml(emptyMsg) + "</li>";
      return;
    }

    counts.sort(function (a, b) {
      if (b.recordsCount !== a.recordsCount) return b.recordsCount - a.recordsCount;
      var nameA = (a.student && a.student.name) || "";
      var nameB = (b.student && b.student.name) || "";
      return nameA.localeCompare(nameB);
    });

    var top = counts.slice(0, 100);
    var items = [];
    for (var i = 0; i < top.length; i++) {
      var entry = top[i];
      var s = entry.student || {};
      var state = s.state || "";
      var displayName = String(s.name || "");
      if (state) {
        displayName += " (" + state + ")";
      }
      var gradeHtml = "";
      var gradeLabel = getGradeLabel(s.grade_in_2026);
      if (gradeLabel) {
        gradeHtml = " <span class=\"awards-ranking-grade\" title=\"Current grade (school year starts Sept 1)\">" + gradeLabel + "</span>";
      }
      var label = entry.recordsCount === 1 ? "record" : "records";
      items.push(
        "<li class=\"awards-ranking-item\">" +
          "<span class=\"awards-ranking-position\">#" + (i + 1) + "</span>" +
          "<span class=\"awards-ranking-name\" data-student-name=\"" + escapeHtml(String(s.name || "")) + "\">" + escapeHtml(displayName) + gradeHtml + "</span>" +
          "<span class=\"awards-ranking-count\" data-student-name=\"" + escapeHtml(String(s.name || "")) + "\">" + escapeHtml(String(entry.recordsCount)) + " " + label + "</span>" +
        "</li>"
      );
    }

    awardsRankingListEl.innerHTML = items.join("");
  }

  function bindContestListPopover() {
    var trigger = document.getElementById("contest-list-trigger");
    var popover = document.getElementById("contest-list-popover");
    var closeBtn = popover && popover.querySelector(".contest-list-popover-close");
    var backdrop = popover && popover.querySelector(".contest-list-popover-backdrop");
    if (!trigger || !popover) return;

    function open() {
      popover.hidden = false;
      trigger.setAttribute("aria-expanded", "true");
    }
    function close() {
      popover.hidden = true;
      trigger.setAttribute("aria-expanded", "false");
    }

    trigger.addEventListener("click", function () {
      if (popover.hidden) open(); else close();
    });
    if (closeBtn) closeBtn.addEventListener("click", close);
    if (backdrop) backdrop.addEventListener("click", close);
  }

  function runSearch() {
    var query = (searchEl && searchEl.value) ? searchEl.value.trim() : "";
    emptyEl.hidden = true;
    resultsEl.innerHTML = "";

    if (searchClearEl) {
      searchClearEl.hidden = !query;
    }

    if (!query) {
      hintEl.textContent = "Enter at least one character to search.";
      if (topStudentsSectionEl) topStudentsSectionEl.hidden = false;
      return;
    }

    var matched = data.students.filter(function (s) { return matchStudent(s, query); });
    hintEl.textContent = matched.length === 0
      ? "No students found."
      : matched.length === 1
        ? "1 student found."
        : matched.length + " students found.";

    if (matched.length === 0) {
      emptyEl.hidden = false;
      if (topStudentsSectionEl) topStudentsSectionEl.hidden = false;
      return;
    }

    if (topStudentsSectionEl) topStudentsSectionEl.hidden = true;

    resultsEl.innerHTML = matched.map(function (s) { return renderStudent(s, data.contests || {}); }).join("");
  }

  function keysForPdfDisplay(records, slug) {
    var keys = allRecordHeaders(records);
    var omit = { p1: 1, p2: 1, p3: 1, p4: 1, p5: 1, p6: 1, p7: 1, p8: 1, p9: 1, p10: 1 };
    if (slug === "dmm") {
      omit.q1 = 1; omit.q2 = 1; omit.q3 = 1; omit.q4 = 1; omit.q5 = 1;
      omit.q6 = 1; omit.q7 = 1; omit.q8 = 1; omit.q9 = 1; omit.q10 = 1;
    }
    return keys.filter(function (k) { return !omit[k]; });
  }

  function exportStudentToPdf(cardEl) {
    if (!cardEl) return;
    var studentId = cardEl.getAttribute("data-student-id");
    if (studentId == null || studentId === "") return;
    var id = parseInt(studentId, 10);
    if (isNaN(id)) return;
    var student = null;
    for (var i = 0; i < data.students.length; i++) {
      if (data.students[i].id === id) {
        student = data.students[i];
        break;
      }
    }
    if (!student) {
      alert("Student data not found.");
      return;
    }
    var JsPDFConstructor = (typeof jspdf !== "undefined" && jspdf.jsPDF) ? jspdf.jsPDF : (typeof jsPDF !== "undefined" ? jsPDF : null);
    if (!JsPDFConstructor) {
      alert("PDF export is not available. Please refresh the page and try again.");
      return;
    }
    var btn = cardEl.querySelector(".export-pdf-student-btn");
    if (btn) btn.disabled = true;
    var studentName = (student.name || "").trim();
    var state = (student.state || "").trim();
    var filename = "math-competition-" + (studentName ? studentName.replace(/\W+/g, "-") : "student") + ".pdf";

    try {
      var doc = new JsPDFConstructor({ orientation: "p", unit: "mm", format: "a4" });
      var margin = 10;
      var y = margin;

      doc.setFontSize(14);
      doc.text(studentName + (state ? " (" + state + ")" : ""), margin, y);
      y += 8;

      if (student.aliases && student.aliases.length) {
        doc.setFontSize(9);
        doc.setTextColor(100, 100, 100);
        doc.text("Also known as: " + student.aliases.join(", "), margin, y);
        doc.setTextColor(0, 0, 0);
        y += 6;
      }

      var records = student.records || [];
      var grouped = groupRecordsByContest(records);
      var slugs = grouped.slugs;
      var bySlug = grouped.bySlug;
      var contestsMap = data.contests || {};

      for (var s = 0; s < slugs.length; s++) {
        var slug = slugs[s];
        var contestRecords = bySlug[slug].slice();
        contestRecords.sort(function (a, b) {
          var yA = a.year || "";
          var yB = b.year || "";
          return yA > yB ? -1 : yA < yB ? 1 : 0;
        });
        var keys = keysForPdfDisplay(contestRecords, slug);
        var contestInfo = contestsMap[slug];
        var contestTitle = (contestInfo && contestInfo.contest_name) ? contestInfo.contest_name : slug.replace(/-/g, " ");

        if (y > 250) {
          doc.addPage();
          y = margin;
        }
        doc.setFontSize(11);
        doc.text(contestTitle, margin, y);
        y += 6;

        var headers = ["Year"].concat(keys.map(function (k) { return k.replace(/_/g, " "); }));
        var body = contestRecords.map(function (r) {
          var row = [r.year != null ? String(r.year) : ""];
          for (var k = 0; k < keys.length; k++) {
            var val = r[keys[k]];
            row.push(val != null ? String(val) : "");
          }
          return row;
        });
        doc.autoTable({
          head: [headers],
          body: body,
          startY: y,
          margin: { left: margin },
          theme: "grid",
          styles: { fontSize: 8 },
          headStyles: { fontSize: 8, fillColor: [96, 165, 250], textColor: [255, 255, 255] }
        });
        y = doc.lastAutoTable.finalY + 10;
      }

      doc.save(filename);
    } catch (err) {
      alert("Failed to generate PDF: " + (err && err.message ? err.message : "Unknown error"));
    }
    if (btn) btn.disabled = false;
  }

  function init() {
    setLoading(true);
    var base = document.querySelector("script[src$='app.js']").src.replace(/\/[^/]*$/, "");
    fetch(base + "/data.json")
      .then(function (res) {
        if (!res.ok) throw new Error("Failed to load data: " + res.status);
        return res.json();
      })
      .then(function (json) {
        data = json;
        var order = json.contest_order || [];
        var orderMap = {};
        if (order && order.length) {
          for (var i = 0; i < order.length; i++) {
            var slug = order[i];
            if (slug != null && orderMap[slug] == null) {
              orderMap[slug] = i;
            }
          }
        }
        data.contest_order_map = orderMap;
        setLoading(false);
        renderContestList();
        renderTopStudentsByRecords();
        bindContestListPopover();
        runSearch();
      })
      .catch(function (err) {
        setLoading(false);
        resultsEl.innerHTML = "<p class=\"empty-state\">Could not load data. " + escapeHtml(String(err.message)) + "</p>";
      });
  }

  if (searchEl) {
    searchEl.addEventListener("input", runSearch);
    searchEl.addEventListener("search", runSearch);
  }

  if (searchClearEl) {
    searchClearEl.addEventListener("click", function () {
      if (!searchEl) return;
      searchEl.value = "";
      runSearch();
      searchEl.focus();
    });
  }

  if (girlsOnlyEl) {
    girlsOnlyEl.addEventListener("change", function () {
      renderTopStudentsByRecords();
    });
  }

  if (gradeFilterEl) {
    gradeFilterEl.addEventListener("change", function () {
      renderTopStudentsByRecords();
    });
  }

  if (resultsEl) {
    resultsEl.addEventListener("click", function (event) {
      var target = event.target;
      if (target && target.classList && target.classList.contains("export-pdf-student-btn")) {
        var card = target.closest(".student-card");
        if (card) exportStudentToPdf(card);
        return;
      }
      if (!target || !target.classList || !target.classList.contains("student-name")) return;
      var nameAttr = target.getAttribute("data-student-name");
      var name = (nameAttr || target.textContent || "").trim();
      if (!name || !searchEl) return;
      searchEl.value = name;
      runSearch();
      searchEl.blur();
      if (typeof searchEl.setSelectionRange === "function") {
        var len = name.length;
        searchEl.setSelectionRange(len, len);
      }
      var firstCard = resultsEl.querySelector(".student-card");
      if (firstCard && typeof firstCard.scrollIntoView === "function") {
        firstCard.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    });
  }

  if (awardsRankingListEl) {
    awardsRankingListEl.addEventListener("click", function (event) {
      var target = event.target;
      while (target && target !== awardsRankingListEl && !target.getAttribute("data-student-name")) {
        target = target.parentNode;
      }
      if (!target || target === awardsRankingListEl) return;
      var name = (target.getAttribute("data-student-name") || target.textContent || "").trim();
      if (!name || !searchEl) return;
      searchEl.value = name;
      runSearch();
      searchEl.blur();
      if (typeof searchEl.setSelectionRange === "function") {
        var len = name.length;
        searchEl.setSelectionRange(len, len);
      }
      var firstCard = resultsEl && resultsEl.querySelector(".student-card");
      if (firstCard && typeof firstCard.scrollIntoView === "function") {
        firstCard.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    });
  }

  // Dismiss keyboard on mobile when tapping outside the search box
  if (searchEl) {
    var searchWrap = document.querySelector(".search-wrap");
    function dismissKeyboardIfOutside(ev) {
      if (!searchEl) return;
      if (searchWrap && searchWrap.contains(ev.target)) return;
      searchEl.blur();
    }
    document.addEventListener("click", dismissKeyboardIfOutside, false);
    document.addEventListener("touchend", dismissKeyboardIfOutside, false);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
