/**
 * AMO 2025 Gold/Silver/Bronze/Honorable Mention alert check.
 * Finds students who have AMO 2025 Gold, Silver, Bronze, or Honorable Mention but no track records in:
 * JMO, previous years AMO, HMMT Feb, HMMT Nov, CMIMC, BAMO-12, PUMaC Div A, ARML.
 * Exposed as window.AmoAlertCheck.getAmo2025GoldSilverNoTrack(students).
 */
(function () {
  "use strict";

  var AMO_YEAR = "2025";
  var AMO_SLUG = "amo";

  function isIncludedAward(award) {
    if (award == null) return false;
    var a = String(award).trim().toLowerCase();
    return a === "gold" || a === "silver" || a === "bronze" || a === "honorable mention";
  }

  /** Sort order for award: Gold first, then Silver, Bronze, Honorable Mention. */
  function awardSortOrder(award) {
    if (!award) return 4;
    var a = String(award).trim().toLowerCase();
    if (a === "gold") return 0;
    if (a === "silver") return 1;
    if (a === "bronze") return 2;
    if (a === "honorable mention") return 3;
    return 4;
  }

  /**
   * Predicates: each takes (slug, year) and returns true if that contest counts as "track".
   * year may be string or number.
   */
  function isJmo(slug) {
    return slug === "jmo";
  }

  function isPreviousAmo(slug, year) {
    return slug === AMO_SLUG && String(year) !== AMO_YEAR;
  }

  function isHmmtFeb(slug) {
    return slug.indexOf("hmmt-feb") === 0;
  }

  function isHmmtNov(slug) {
    return slug.indexOf("hmmt-nov") === 0;
  }

  function isCmimc(slug) {
    return slug.indexOf("cmimc") !== -1;
  }

  function isBamo12(slug) {
    return slug.indexOf("bamo-12") !== -1;
  }

  function isPumacA(slug) {
    if (slug.indexOf("pumac-b") === 0) return false;
    return slug.indexOf("pumac") === 0;
  }

  function isArml(slug) {
    return slug.indexOf("arml") !== -1;
  }

  function isTrackRecord(record) {
    if (!record) return false;
    var slug = (record.contest_slug || record.contest || "").toString().toLowerCase();
    var year = record.year != null ? record.year : "";
    if (!slug) return false;
    return isJmo(slug) ||
      isPreviousAmo(slug, year) ||
      isHmmtFeb(slug) ||
      isHmmtNov(slug) ||
      isCmimc(slug) ||
      isBamo12(slug) ||
      isPumacA(slug) ||
      isArml(slug);
  }

  function hasAmo2025GoldOrSilver(records) {
    if (!records || !records.length) return false;
    for (var i = 0; i < records.length; i++) {
      var r = records[i];
      var slug = (r.contest_slug || r.contest || "").toString().toLowerCase();
      var year = r.year != null ? String(r.year) : "";
      if (slug === AMO_SLUG && year === AMO_YEAR && isIncludedAward(r.award)) {
        return true;
      }
    }
    return false;
  }

  function hasAnyTrackRecord(records) {
    if (!records || !records.length) return false;
    for (var j = 0; j < records.length; j++) {
      if (isTrackRecord(records[j])) return true;
    }
    return false;
  }

  /**
   * @param {Array<{ id: number, name: string, records: Array }>} students
   * @returns {Array<{ id: number, name: string, state: string, award: string }>} students who are AMO 2025 Gold/Silver/Bronze/Honorable Mention
   *   and have no track record in JMO, previous AMO, hmmt-feb, hmmt-nov, cmimc, bamo-12, pumac div A, arml.
   */
  function getAmo2025GoldSilverNoTrack(students) {
    if (!students || !students.length) return [];
    var out = [];
    for (var i = 0; i < students.length; i++) {
      var s = students[i];
      var records = s.records || [];
      if (!hasAmo2025GoldOrSilver(records)) continue;
      if (hasAnyTrackRecord(records)) continue;
      var amoRec = null;
      for (var k = 0; k < records.length; k++) {
        var r = records[k];
        var slug = (r.contest_slug || r.contest || "").toString().toLowerCase();
        var year = r.year != null ? String(r.year) : "";
        if (slug === AMO_SLUG && year === AMO_YEAR && isIncludedAward(r.award)) {
          amoRec = r;
          break;
        }
      }
      out.push({
        id: s.id,
        name: s.name || "",
        state: (s.state || "").trim(),
        award: amoRec && amoRec.award ? String(amoRec.award).trim() : ""
      });
    }
    out.sort(function (a, b) {
      var orderA = awardSortOrder(a.award);
      var orderB = awardSortOrder(b.award);
      if (orderA !== orderB) return orderA - orderB;
      return (a.name || "").localeCompare(b.name || "");
    });
    return out;
  }

  window.AmoAlertCheck = {
    getAmo2025GoldSilverNoTrack: getAmo2025GoldSilverNoTrack
  };
})();
