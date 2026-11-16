import { browserStorage } from "@/utils/browser-storage";
const PREFIX = "autocomplete_";

class TextHistory {
  constructor(namespace) {
    this.namespace = PREFIX + namespace;
  }

  getTexts() {
    let texts = browserStorage.getItem(this.namespace);

    if (!texts) {
      texts = [];
      browserStorage.setItem(this.namespace, JSON.stringify(texts));
    } else {
      try { texts = JSON.parse(texts); } catch { texts = []; }
      if (!Array.isArray(texts)) texts = [];
      texts = texts.filter((item) => typeof item === "string");
    }

    texts.sort((a, b) => a.toLowerCase() > b.toLowerCase());

    return texts;
  }

  saveText(text, sharedMessages = []) {
    if (!text || sharedMessages.includes(text)) {
      return;
    }
    const texts = this.getTexts();
    texts.push(text);
    browserStorage.setItem(this.namespace, JSON.stringify([...new Set(texts)]));
  }

  clear() {
    browserStorage.removeItem(this.namespace);
  }
}

export default TextHistory;
export { TextHistory };
