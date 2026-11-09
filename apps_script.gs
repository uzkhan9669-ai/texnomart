// Google Tablitsa uchun qabul qiluvchi skript (Apps Script).
// O'rnatish: Google Tablitsa -> Kengaytmalar (Extensions) -> Apps Script -> shu kodni qo'ying ->
// SECRET ni o'zgartiring -> "Deploy" -> "New deployment" -> turi "Web app" ->
// "Execute as: Me", "Who has access: Anyone" -> manzilni (.../exec) botdagi SHEETS_URL ga qo'ying.
// Kalit: Telegram ID (ustun A). Nomzod qayta to'ldirsa yoki holati o'zgarsa, qator yangilanadi.
// Kodni o'zgartirsangiz, "Deploy" -> "Manage deployments" -> yangi versiya chiqaring.

var SECRET = "BU_YERGA_MAXFIY_SOZ_YOZING";   // botdagi SHEETS_SECRET bilan bir xil bo'lsin
var SHEET_NAME = "Nomzodlar";
var HEADERS = ["Telegram ID", "Sana", "F.I.Sh.", "Yosh", "Telefon", "Telegram", "Hudud", "Moslik %",
               "Tavsiya", "Qizil", "Sariq", "Holat", "Flaglar", "Javoblar (JSON)"];

function doPost(e) {
  try {
    var p = JSON.parse(e.postData.contents);
    if (p.secret !== SECRET) return reply({ ok: false, error: "forbidden" });

    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var sh = ss.getSheetByName(SHEET_NAME) || ss.insertSheet(SHEET_NAME);
    if (sh.getLastRow() === 0) {
      sh.appendRow(HEADERS);
      sh.setFrozenRows(1);
    }
    var row = [String(p.tg_id), p.ts, p.fio, p.age, p.phone, p.username ? "@" + p.username : "", p.district,
               p.pct, p.verdict, p.red, p.yellow, p.status, p.flags, p.answers];

    var lock = LockService.getScriptLock();
    lock.waitLock(20000);
    try {
      var last = sh.getLastRow();
      var at = -1;
      if (last > 1) {
        var ids = sh.getRange(2, 1, last - 1, 1).getValues();
        for (var i = 0; i < ids.length; i++) {
          if (String(ids[i][0]) === String(p.tg_id)) { at = i + 2; break; }
        }
      }
      if (at > 0) sh.getRange(at, 1, 1, row.length).setValues([row]);
      else sh.appendRow(row);
    } finally {
      lock.releaseLock();
    }
    return reply({ ok: true });
  } catch (err) {
    return reply({ ok: false, error: String(err) });
  }
}

function reply(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}
