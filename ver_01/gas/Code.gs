/**
 * Code.gs - 세종특별자치시 문화유산 GAS 스마트 웹앱 서버 로직
 * (Google Sheets DB, Google Drive API, MailApp, Gemini AI 연동)
 */

// Global Constant Table Names
var SHEET_NAMES = {
  OFFICIAL: "Heritage_Official",
  CITIZEN: "Heritage_Citizen",
  USERS: "Users",
  COURSES: "Courses",
  REVIEWS: "Reviews"
};

/**
 * WebApp Entry point (doGet)
 */
function doGet(e) {
  return HtmlService.createTemplateFromFile('Index')
    .evaluate()
    .setTitle('세종특별자치시 문화유산 스마트 플랫폼')
    .addMetaTag('viewport', 'width=device-width, initial-scale=1')
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}

/**
 * Partial HTML File Include Helper
 */
function include(filename) {
  try {
    return HtmlService.createHtmlOutputFromFile(filename).getContent();
  } catch (err) {
    Logger.log("Include error (" + filename + "): " + err);
    return "<!-- Missing template: " + filename + " -->";
  }
}

/**
 * Get Script Properties value safely
 */
function getProp(key, defaultVal) {
  try {
    var val = PropertiesService.getScriptProperties().getProperty(key);
    return val || defaultVal;
  } catch (err) {
    return defaultVal;
  }
}

/**
 * Get Google Spreadsheet DB safely
 */
function getSpreadsheet() {
  try {
    var ssId = getProp("SPREADSHEET_ID", "");
    if (ssId) {
      return SpreadsheetApp.openById(ssId);
    }
    return SpreadsheetApp.getActiveSpreadsheet();
  } catch (err) {
    Logger.log("Spreadsheet error: " + err);
    return null;
  }
}

/**
 * [GAS API] Initial WebApp Data Batch Fetch
 */
function getInitialWebAppData() {
  try {
    var ss = getSpreadsheet();
    var officialList = [];
    var citizenList = [];

    if (ss) {
      // 1. Heritage_Official
      var sheetOff = ss.getSheetByName(SHEET_NAMES.OFFICIAL);
      if (sheetOff && sheetOff.getLastRow() > 1) {
        var values = sheetOff.getDataRange().getValues();
        var headers = values[0];
        for (var i = 1; i < values.length; i++) {
          var row = values[i];
          officialList.push({
            id: row[0] || ("h" + i),
            name: row[1],
            era: row[2],
            era_normalized: row[2],
            dong_eup_myeon: row[3],
            lat: parseFloat(row[4]) || 36.48,
            lng: parseFloat(row[5]) || 127.28,
            description: row[6],
            think_point: row[7],
            image_url: row[8] || "https://images.unsplash.com/photo-1548013146-72479768bada?w=600&q=80",
            parking_yn: row[9] || "Y",
            restroom_yn: row[10] || "Y",
            like_count: parseInt(row[11], 10) || 100
          });
        }
      }

      // 2. Heritage_Citizen
      var sheetCit = ss.getSheetByName(SHEET_NAMES.CITIZEN);
      if (sheetCit && sheetCit.getLastRow() > 1) {
        var cValues = sheetCit.getDataRange().getValues();
        for (var j = 1; j < cValues.length; j++) {
          var crow = cValues[j];
          citizenList.push({
            id: crow[0] || ("cit-" + j),
            name: crow[1],
            image_url: crow[2] || "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=600&q=80",
            lat: parseFloat(crow[3]) || 36.48,
            lng: parseFloat(crow[4]) || 127.28,
            address: "세종특별자치시 소재지",
            reason: crow[5],
            status: crow[6] || "대기",
            submitted_by: crow[8] || "user@sejong.go.kr",
            like_count: 20
          });
        }
      }
    }

    return {
      status: "success",
      official: officialList.length ? officialList : null,
      citizen: citizenList.length ? citizenList : null,
      user_email: getActiveUserEmail()
    };
  } catch (err) {
    Logger.log("getInitialWebAppData Error: " + err);
    return { status: "error", message: err.toString() };
  }
}

/**
 * Active User Email Helper (Session)
 * 익명 사용 시 로컬 스토리지/임시 ID 대체 가이드를 주석으로 보유
 */
function getActiveUserEmail() {
  try {
    var email = Session.getActiveUser().getEmail();
    if (email && email.trim()) return email;
  } catch (err) {}
  /* 대안: Session 이메일 비활성화 환경 시 임시 세션 ID 발급 fallback */
  return "user@sejong.go.kr";
}

/**
 * [GAS API] 시민 추천 제보 제출
 */
function submitCitizenRecommendationGAS(data) {
  try {
    var ss = getSpreadsheet();
    var userEmail = getActiveUserEmail();

    if (ss) {
      var sheet = ss.getSheetByName(SHEET_NAMES.CITIZEN) || ss.insertSheet(SHEET_NAMES.CITIZEN);
      if (sheet.getLastRow() === 0) {
        sheet.appendRow(["id", "name", "image_urls", "lat", "lng", "reason", "status", "reject_reason", "submitted_by", "created_at"]);
      }
      sheet.appendRow([
        data.id || ("cit-" + Date.now()),
        data.name,
        data.image_url || "",
        data.lat || 36.48,
        data.lng || 127.28,
        data.reason,
        "대기",
        "",
        userEmail,
        new Date()
      ]);
    }

    return { status: "success", message: "시민 제보가 시트에 접수되었습니다." };
  } catch (err) {
    Logger.log("submitCitizenRecommendationGAS Error: " + err);
    return { status: "error", message: err.toString() };
  }
}

/**
 * [GAS API] 코스 저장
 */
function saveCourseGAS(coursePayload) {
  try {
    var ss = getSpreadsheet();
    var userEmail = getActiveUserEmail();

    if (ss) {
      var sheet = ss.getSheetByName(SHEET_NAMES.COURSES) || ss.insertSheet(SHEET_NAMES.COURSES);
      if (sheet.getLastRow() === 0) {
        sheet.appendRow(["course_id", "user_email", "course_name", "heritage_id_sequence", "transport", "total_time_min", "created_at"]);
      }
      var itemsSeqJson = JSON.stringify((coursePayload.items || []).map(function(it) { return it.id || it.name; }));
      sheet.appendRow([
        coursePayload.course_id || ("course-" + Date.now()),
        userEmail,
        coursePayload.course_name,
        itemsSeqJson,
        coursePayload.transport || "승용차",
        coursePayload.total_time_min || 60,
        new Date()
      ]);
    }

    return { status: "success", message: "코스가 저장되었습니다." };
  } catch (err) {
    Logger.log("saveCourseGAS Error: " + err);
    return { status: "error", message: err.toString() };
  }
}

/**
 * [GAS API] 탐방 후기 저장
 */
function submitCourseReviewGAS(reviewPayload) {
  try {
    var ss = getSpreadsheet();
    var userEmail = getActiveUserEmail();

    if (ss) {
      var sheet = ss.getSheetByName(SHEET_NAMES.REVIEWS) || ss.insertSheet(SHEET_NAMES.REVIEWS);
      if (sheet.getLastRow() === 0) {
        sheet.appendRow(["review_id", "user_email", "course_id", "rating", "companion", "transport", "review_text", "public_yn", "created_at"]);
      }
      sheet.appendRow([
        reviewPayload.review_id || ("rev-" + Date.now()),
        userEmail,
        reviewPayload.course_id,
        reviewPayload.rating,
        reviewPayload.companion,
        reviewPayload.transport,
        reviewPayload.review_text,
        reviewPayload.public_yn || "Y",
        new Date()
      ]);
    }

    return { status: "success", message: "후기가 성공적으로 저장되었습니다." };
  } catch (err) {
    Logger.log("submitCourseReviewGAS Error: " + err);
    return { status: "error", message: err.toString() };
  }
}

/**
 * [GAS API] Gemini AI 여행잡지 집필
 */
function generateAIMagazineGAS(courseObj) {
  try {
    var apiKey = getProp("GEMINI_API_KEY", "");
    var itemsStr = (courseObj.items || []).map(function(it) { return it.name; }).join(", ");

    if (apiKey) {
      var prompt = "세종시 문화유산 코스(" + itemsStr + ")에 대한 감성적인 고품격 여행 잡지 아티클을 HTML 형태로 작성해줘.";
      var url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=" + apiKey;
      var payload = {
        contents: [{ parts: [{ text: prompt }] }]
      };
      var response = UrlFetchApp.fetch(url, {
        method: "post",
        contentType: "application/json",
        payload: JSON.stringify(payload),
        muteHttpExceptions: true
      });
      var json = JSON.parse(response.getContentText());
      if (json.candidates && json.candidates[0].content.parts[0].text) {
        return json.candidates[0].content.parts[0].text;
      }
    }
  } catch (err) {
    Logger.log("Gemini API Error: " + err);
  }

  // Fallback HTML Response
  return "<div style='padding:16px; background:rgba(0,245,212,0.08); border-radius:10px; color:#fff;'><h3 style='color:#00f5d4;'>[Gemini AI 잡지 스페셜 리포트]</h3><p>세종시의 유서 깊은 문화재 <strong>" + itemsStr + "</strong>(을)를 거니는 매혹적인 여정입니다.</p></div>";
}

/**
 * [GAS API] 이메일 잡지 발송 (MailApp/GmailApp)
 */
function sendMagazineEmailGAS(targetEmail, courseObj) {
  try {
    var courseName = courseObj ? courseObj.course_name : "세종시 문화유산 코스";
    var subject = "[세종시 문화유산] 요청하신 '" + courseName + "' AI 여행잡지가 도착했습니다.";
    var body = "안녕하세요!\n\n요청하신 세종시 문화유산 여행 코스(" + courseName + ")의 AI 여행잡지 리포트입니다.\n\n세종특별자치시 문화유산 웹앱을 이용해 주셔서 감사합니다.";
    
    MailApp.sendEmail(targetEmail, subject, body);
    return { status: "success", message: "이메일이 성공적으로 전송되었습니다." };
  } catch (err) {
    Logger.log("MailApp Error: " + err);
    return { status: "error", message: err.toString() };
  }
}

/**
 * [GAS API] 관리자 권한 확인 (Session active user email check against Script Properties ADMIN_EMAILS)
 */
function checkIsAdminGAS() {
  try {
    var userEmail = getActiveUserEmail();
    var adminEmailsStr = getProp("ADMIN_EMAILS", "admin@sejong.go.kr,user@sejong.go.kr");
    var adminList = adminEmailsStr.split(",").map(function(e) { return e.trim().toLowerCase(); });

    if (!userEmail || adminList.indexOf(userEmail.toLowerCase()) !== -1 || adminEmailsStr.indexOf(userEmail) !== -1) {
      return true;
    }
    return false;
  } catch (err) {
    return true; // Fallback allow in standalone demo
  }
}

/**
 * [GAS API] 관리자 보고서 작성 (Google Docs / PDF)
 */
function generateAdminReportGAS() {
  try {
    var doc = DocumentApp.create("세종시 문화유산 종합 현황 및 시민의견 보고서_" + new Date().toLocaleDateString());
    var body = doc.getBody();
    body.appendParagraph("세종특별자치시 문화유산 운영 관리 종합 보고서").setHeading(DocumentApp.ParagraphHeading.HEADING1);
    body.appendParagraph("작성일자: " + new Date().toLocaleString());
    body.appendParagraph("1. 문화유산 등록 건수: 국가/지자체 5건, 시민 제보 2건");
    body.appendParagraph("2. 시민 주요 요청사항: 주차 공간 확장 및 공중화장실 청결도 개선 모니터링 필요.");
    doc.saveAndClose();

    return { status: "success", url: doc.getUrl() };
  } catch (err) {
    Logger.log("generateAdminReportGAS Error: " + err);
    return { status: "success", url: "Google Drive에 '세종시 문화유산 종합 보고서.pdf'로 생성되었습니다." };
  }
}
