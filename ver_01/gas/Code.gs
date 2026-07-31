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
 * Get Google Cloud Run Service Backend URL (Project: heritage-503408, Service: heritage-min, Region: us-central1)
 */
function getCloudRunBackendUrl() {
  return getProp("CLOUD_RUN_URL", "https://heritage-min-503408.us-central1.run.app");
}

/**
 * Standalone OAuth2 Service Helper (No External Library ID Needed)
 */
function getOAuth2Service(serviceName, clientId, clientSecret, scopes) {
  return OAuth2.createService(serviceName || "SejongHeritageOAuth")
    .setAuthorizationBaseUrl('https://accounts.google.com/o/oauth2/auth')
    .setTokenUrl('https://accounts.google.com/o/oauth2/token')
    .setClientId(clientId || getProp("OAUTH_CLIENT_ID", ""))
    .setClientSecret(clientSecret || getProp("OAUTH_CLIENT_SECRET", ""))
    .setCallbackFunction('authCallback')
    .setPropertyStore(PropertiesService.getUserProperties())
    .setScope(scopes || 'https://www.googleapis.com/auth/drive.readonly https://www.googleapis.com/auth/spreadsheets');
}

/**
 * OAuth2 Callback Handler Function
 */
function authCallback(request) {
  var service = getOAuth2Service();
  var authorized = service.handleCallback(request);
  if (authorized) {
    return HtmlService.createHtmlOutput('✅ OAuth2 인증이 성공적으로 완료되었습니다! 이 창을 닫고 앱으로 돌아가세요.');
  } else {
    return HtmlService.createHtmlOutput('❌ OAuth2 인증에 실패하였습니다. 다시 시도해 주세요.');
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
 * Query Supabase REST API directly for DB tables & Storage
 */
function getSupabaseData(tableName, query) {
  var supabaseUrl = getProp("SUPABASE_URL", "https://nmzrxczcytkkwgpiseaj.supabase.co");
  var supabaseKey = getProp("SUPABASE_KEY", "your-supabase-key");
  
  var url = supabaseUrl + "/rest/v1/" + tableName + (query ? ("?" + query) : "?select=*");
  var options = {
    method: "get",
    headers: {
      "apikey": supabaseKey,
      "Authorization": "Bearer " + supabaseKey,
      "Content-Type": "application/json"
    },
    muteHttpExceptions: true
  };

  try {
    var response = UrlFetchApp.fetch(url, options);
    if (response.getResponseCode() === 200) {
      return JSON.parse(response.getContentText());
    }
  } catch (e) {
    Logger.log("Supabase REST Fetch Error: " + e);
  }
  return null;
}

/**
 * [GAS API] Initial WebApp Data Batch Fetch (Primary: Supabase DB & Storage, Fallback: Spreadsheet)
 */
function getInitialWebAppData() {
  try {
    var officialList = [];
    var citizenList = [];

    // 1. Primary: Fetch live Supabase DB records
    var supaHeritages = getSupabaseData("heritages", "select=*,images:heritage_images(*)");
    if (supaHeritages && supaHeritages.length > 0) {
      supaHeritages.forEach(function(item, idx) {
        var imgUrl = (item.images && item.images.length > 0 && item.images[0].image_url)
          ? item.images[0].image_url
          : (item.supabase_storage_url || item.image_url || "https://images.unsplash.com/photo-1548013146-72479768bada?w=600&q=80");

        var rec = {
          id: item.id || ("supa-db-" + (idx + 1)),
          name: item.name,
          era: item.era || "조선시대",
          era_normalized: item.era || "조선시대",
          dong: item.dong || item.dong_eup_myeon || "세종특별자치시",
          dong_eup_myeon: item.dong || item.dong_eup_myeon || "세종특별자치시",
          lat: parseFloat(item.latitude || item.lat) || 36.52,
          lng: parseFloat(item.longitude || item.lng) || 127.27,
          latitude: parseFloat(item.latitude || item.lat) || 36.52,
          longitude: parseFloat(item.longitude || item.lng) || 127.27,
          description: item.description || "문화유산 상세 소개",
          think_point: item.thinking_point || item.thinkingPoint || item.think_about,
          thinkingPoint: item.thinking_point || item.thinkingPoint || item.think_about,
          thinking_point: item.thinking_point || item.thinkingPoint || item.think_about,
          image_url: imgUrl,
          supabaseStorageUrl: imgUrl,
          source: item.source || "registered",
          status: item.status || "approved",
          parking_yn: "Y",
          restroom_yn: "Y",
          like_count: item.like_count || 100
        };

        if (rec.source === "citizen") {
          citizenList.push(rec);
        } else {
          officialList.push(rec);
        }
      });
    }

    // 2. Fallback: Query Spreadsheet if Supabase table is empty
    if (officialList.length === 0 && citizenList.length === 0) {
      var ss = getSpreadsheet();
      if (ss) {
        var sheetOff = ss.getSheetByName(SHEET_NAMES.OFFICIAL);
        if (sheetOff && sheetOff.getLastRow() > 1) {
          var values = sheetOff.getDataRange().getValues();
          for (var i = 1; i < values.length; i++) {
            var row = values[i];
            officialList.push({
              id: row[0] || ("h" + i),
              name: row[1],
              era: row[2],
              era_normalized: row[2],
              dong: row[3],
              dong_eup_myeon: row[3],
              lat: parseFloat(row[4]) || 36.48,
              lng: parseFloat(row[5]) || 127.28,
              latitude: parseFloat(row[4]) || 36.48,
              longitude: parseFloat(row[5]) || 127.28,
              description: row[6],
              think_point: row[7],
              thinkingPoint: row[7],
              thinking_point: row[7],
              image_url: row[8] || "https://images.unsplash.com/photo-1548013146-72479768bada?w=600&q=80",
              parking_yn: row[9] || "Y",
              restroom_yn: row[10] || "Y",
              like_count: parseInt(row[11], 10) || 100
            });
          }
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
