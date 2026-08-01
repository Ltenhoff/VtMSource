/* Nocturne Archive native PDF bridge. Never rebuilds, flattens, or rasterizes PDFs. */
(function () {
  "use strict";
  function connect() {
    return new Promise((resolve, reject) => {
      if (!window.qt || !window.qt.webChannelTransport) return reject(new Error("The native PDF bridge is unavailable."));
      if (window.pdfBridge) return resolve(window.pdfBridge);
      new QWebChannel(window.qt.webChannelTransport, (channel) => {
        window.pdfBridge = channel.objects.pdfBridge;
        resolve(window.pdfBridge);
      });
    });
  }
  async function call(method, ...args) {
    const bridge = await connect();
    return new Promise((resolve, reject) => {
      try { bridge[method](...args, resolve); } catch (error) { reject(error); }
    });
  }
  window.NocturnePdf = Object.freeze({
    setActiveCharacter: (id) => call("setActiveCharacter", String(id)),
    requestNativeSave: (id) => call("requestNativeSave", String(id)),
    ensureCharacterPdf: (id, ruleset) => call("ensureCharacterPdf", String(id), String(ruleset)),
    importCharacterPdf: (id) => call("importCharacterPdf", String(id)),
    saveCharacterPdfBytes: (id, data) => call("saveCharacterPdfBytes", String(id), String(data)),
    exportCharacterPdf: (id, name) => call("exportCharacterPdf", String(id), String(name || "character-sheet.pdf")),
    resetCharacterPdf: (id, ruleset) => call("resetCharacterPdf", String(id), String(ruleset)),
  });
})();
