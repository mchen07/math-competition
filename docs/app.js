(function () {
  "use strict";

  var data = { students: [], contests: {} };
  var searchEl = document.getElementById("search");
  var resultsEl = document.getElementById("results");
  var emptyEl = document.getElementById("empty");
  var loadingEl = document.getElementById("loading");
  var hintEl = document.getElementById("search-hint");

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

  function renderRecordRow(record, allKeys) {
    var cells = [
      "<td class=\"num\">", escapeHtml(record.year || ""), "</td>"
    ];
    for (var i = 0; i < allKeys.length; i++) {
      var key = allKeys[i];
      var val = record[key] != null ? record[key] : "";
      var cellClass = key === "rank" ? "num rank-" + (val === "1" || val === 1 ? "1" : (val === "2" || val === 2 || val === "3" || val === 3 ? "2" : "")) : "num";
      cells.push("<td class=\"" + cellClass + "\">", escapeHtml(String(val)), "</td>");
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
    slugs.sort();
    return { bySlug: bySlug, slugs: slugs };
  }

  function renderStudent(student, contestsMap) {
    var records = student.records || [];
    var grouped = groupRecordsByContest(records);
    var bySlug = grouped.bySlug;
    var slugs = grouped.slugs;

    var sections = [];
    for (var i = 0; i < slugs.length; i++) {
      var slug = slugs[i];
      var contestRecords = bySlug[slug];
      contestRecords.sort(function (a, b) {
        var yA = a.year || "";
        var yB = b.year || "";
        return yA > yB ? -1 : yA < yB ? 1 : 0;
      });
      var headers = ["Year"].concat(allRecordHeaders(contestRecords));
      var headerCells = headers.map(function (h) {
        var label = h.replace(/_/g, " ");
        return "<th>" + escapeHtml(label) + "</th>";
      }).join("");
      var allKeys = allRecordHeaders(contestRecords);
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

    return (
      "<article class=\"student-card\" data-student-id=\"" + escapeHtml(String(student.id)) + "\">" +
        "<div class=\"student-header\">" +
          "<h2 class=\"student-name\">" + escapeHtml(student.name) + "</h2>" +
          aliasesHtml +
        "</div>" +
        "<div class=\"student-contests\">" + sections.join("") + "</div>" +
      "</article>"
    );
  }

  function runSearch() {
    var query = (searchEl && searchEl.value) ? searchEl.value.trim() : "";
    emptyEl.hidden = true;
    resultsEl.innerHTML = "";

    if (!query) {
      hintEl.textContent = "Enter at least one character to search.";
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
      return;
    }

    resultsEl.innerHTML = matched.map(function (s) { return renderStudent(s, data.contests || {}); }).join("");
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
        setLoading(false);
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

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
