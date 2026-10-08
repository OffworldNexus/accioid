/**
 * Accioid's rough action list card.
 *
 * Deliberately unstyled: ticket 1 only needs a real display path over the
 * WebSocket API. It lists the open actions and refreshes whenever the
 * integration pushes a lifecycle change.
 */

const CARD_TYPE = "accioid-actions-card";

const SEVERITY_LABEL = {
  maintenance: "Maintenance",
  suggestion: "Suggestion",
  emergency: "Emergency",
};

class AccioidActionsCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._actions = [];
    this._error = null;
    this._subscribed = false;
  }

  setConfig(config) {
    this._config = config || {};
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._subscribed) {
      this._subscribed = true;
      this._subscribe();
      this._refresh();
    }
  }

  connectedCallback() {
    this._render();
  }

  disconnectedCallback() {
    this._subscribed = false;
    if (this._unsub) {
      const unsub = this._unsub;
      this._unsub = undefined;
      Promise.resolve(unsub).then((fn) => fn && fn());
    }
  }

  async _subscribe() {
    if (!this._hass) return;
    try {
      this._unsub = this._hass.connection.subscribeMessage(
        () => this._refresh(),
        { type: "accioid/action/subscribe" }
      );
    } catch (err) {
      this._error = `Could not subscribe: ${err.message || err}`;
      this._render();
    }
  }

  async _refresh() {
    if (!this._hass) return;
    try {
      const result = await this._hass.callWS({
        type: "accioid/action/list",
        state: "open",
      });
      this._actions = result.actions || [];
      this._error = null;
    } catch (err) {
      this._error = `Could not load actions: ${err.message || err}`;
    }
    this._render();
  }

  _render() {
    if (!this.shadowRoot) return;
    const title = (this._config && this._config.title) || "Accioid actions";
    let body;
    if (this._error) {
      body = `<p class="error">${this._error}</p>`;
    } else if (this._actions.length === 0) {
      body = `<p class="empty">No open actions.</p>`;
    } else {
      body = `<ul>${this._actions.map((a) => this._row(a)).join("")}</ul>`;
    }
    this.shadowRoot.innerHTML = `
      <style>
        ha-card { padding: 16px; }
        h2 { margin: 0 0 8px; font-size: 1rem; }
        ul { list-style: none; margin: 0; padding: 0; }
        li { padding: 6px 0; border-top: 1px solid var(--divider-color, #e0e0e0); }
        li:first-child { border-top: none; }
        .title { font-weight: 500; }
        .meta { color: var(--secondary-text-color, #727272); font-size: 0.85rem; }
        .empty, .error { color: var(--secondary-text-color, #727272); }
      </style>
      <ha-card>
        <h2>${title}</h2>
        ${body}
      </ha-card>
    `;
  }

  _row(action) {
    const severity = SEVERITY_LABEL[action.severity] || action.severity;
    const area =
      (action.location && action.location.area_name) || "Unassigned room";
    return `<li>
      <div class="title">${action.title}</div>
      <div class="meta">${severity} · ${area}</div>
    </li>`;
  }

  getCardSize() {
    return 1 + Math.ceil(this._actions.length / 2);
  }
}

if (!customElements.get(CARD_TYPE)) {
  customElements.define(CARD_TYPE, AccioidActionsCard);
}

window.customCards = window.customCards || [];
window.customCards.push({
  type: CARD_TYPE,
  name: "Accioid Actions",
  description: "Lists the open Accioid actions (rough, unstyled).",
});
