/**
 * Serves the single-page Web App (Login / Registro / Chat).
 * Set the Cloud Run backend URL once via Script Properties:
 *   Project Settings -> Script Properties -> BACKEND_URL = https://<service>.run.app
 */
function doGet() {
  return HtmlService.createTemplateFromFile('Index')
    .evaluate()
    .setTitle('Elden Ring Guide')
    .addMetaTag('viewport', 'width=device-width, initial-scale=1')
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}

function include(filename) {
  return HtmlService.createHtmlOutputFromFile(filename).getContent();
}

function getBackendUrl() {
  return PropertiesService.getScriptProperties().getProperty('BACKEND_URL') || '';
}
