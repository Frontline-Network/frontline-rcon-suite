(() => {
  const element = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text) node.textContent = text;
    return node;
  };
  const initialize = () => document.querySelectorAll("select.crcon-permission-select").forEach((select) => {
    if (select.dataset.enhanced) return;
    const data = JSON.parse(document.getElementById(select.id + "_help").textContent);
    const de = data.german;
    const own = new Set(Array.from(select.selectedOptions, (option) => option.value));
    const options = new Map(Array.from(select.options, (option) => [option.value, option]));
    const permissions = data.permissions.filter((item) => options.has(item.id));
    // Keep the native select as Django's source of truth, including popup additions.
    const groupSelect = document.querySelector("select.crcon-group-select");
    if (groupSelect && !groupSelect.dataset.enhanced) {
      const groupRoot = element("section", "crcon-group-picker");
      groupRoot.setAttribute("aria-label", de ? "Gruppen auswählen" : "Choose groups");
      const groupIntro = element("p", "permission-intro", de ? "Alle Rechte der ausgewählten Gruppen gelten für dieses Konto. Einzelne Rechte kannst du darunter ergänzen." : "This account inherits every permission from its selected groups. Add individual permissions below.");
      const groupSearch = element("input"); groupSearch.type = "search";
      groupSearch.placeholder = de ? "Gruppen suchen …" : "Search groups …";
      groupSearch.setAttribute("aria-label", de ? "Gruppen durchsuchen" : "Search groups");
      const groupList = element("div", "crcon-group-options");
      const groupCount = element("p", "permission-count"); groupCount.setAttribute("aria-live", "polite");
      const renderGroups = () => {
        groupList.replaceChildren();
        const needle = groupSearch.value.trim().toLocaleLowerCase();
        let matches = 0;
        Array.from(groupSelect.options).forEach(option => {
          if (!option.value || !option.textContent.toLocaleLowerCase().includes(needle)) return;
          matches++;
          const label = element("label", "crcon-group-option");
          const checkbox = element("input"); checkbox.type = "checkbox"; checkbox.checked = option.selected;
          const body = element("span"); body.append(element("strong", "", option.textContent));
          const count = data.groups.find(group => group.id === option.value)?.permissions.length;
          if (count !== undefined) body.append(element("small", "", de ? `${count} Berechtigungen` : `${count} permissions`));
          checkbox.addEventListener("change", () => {
            option.selected = checkbox.checked;
            groupSelect.dispatchEvent(new Event("change", {bubbles:true}));
          });
          label.append(checkbox, body); groupList.append(label);
        });
        if (!matches) groupList.append(element("p", "permission-empty", de ? "Keine passenden Gruppen gefunden." : "No matching groups found."));
        updateGroupCount();
      };
      const updateGroupCount = () => {
        const n = groupSelect.selectedOptions.length;
        groupCount.textContent = de ? `${n} ${n === 1 ? "Gruppe" : "Gruppen"} ausgewählt · Änderungen werden mit dem Formular gespeichert.` : `${n} ${n === 1 ? "group" : "groups"} selected · Changes are saved with the form.`;
      };
      groupRoot.append(groupIntro, groupSearch, groupList, groupCount);
      groupSearch.addEventListener("input", renderGroups);
      groupSelect.addEventListener("change", updateGroupCount);
      new MutationObserver(renderGroups).observe(groupSelect, {childList:true});
      groupSelect.after(groupRoot); groupSelect.hidden = true; groupSelect.dataset.enhanced = "true";
      renderGroups();
      const addGroup = document.getElementById("add_id_groups");
      if (addGroup) {
        addGroup.classList.add("crcon-create-group");
        const label = de ? "Gruppe anlegen" : "Create group";
        addGroup.append(document.createTextNode(label)); addGroup.setAttribute("aria-label", label);
      }
    }
    const root = element("section", "permission-picker");
    root.setAttribute("aria-label", de ? "Berechtigungen auswählen" : "Choose permissions");
    const intro = element("p", "permission-intro", data.direct
      ? (de ? "Direkte Rechte ergänzen die Rechte aus den ausgewählten Gruppen. Gruppenrechte können hier nicht entzogen werden." : "Direct permissions add to the selected groups. Group permissions cannot be revoked here.")
      : (de ? "Diese Rechte gelten für alle Mitglieder der Gruppe. Änderungen werden erst mit dem Formular gespeichert." : "These permissions apply to all group members. Changes take effect when the form is saved."));
    const superuser = element("p", "permission-superuser", de ? "Administrator-Status ist aktiv: Dieses Konto besitzt alle Rechte. Die Einzelauswahl schränkt diese Vollrechte nicht ein." : "Superuser status is active: this account has all permissions. Individual selections do not restrict that access.");
    const toolbar = element("div", "permission-toolbar");
    const search = element("input"); search.type = "search";
    search.placeholder = de ? "Rechte suchen, z. B. kicken, Karten, VIP …" : "Search permissions, e.g. kick, maps, VIP …";
    search.setAttribute("aria-label", de ? "Berechtigungen durchsuchen" : "Search permissions");
    const filterLabel = element("label", "permission-assigned-label");
    const assigned = element("input"); assigned.type = "checkbox";
    filterLabel.append(assigned, document.createTextNode(de ? "Nur vergebene Rechte" : "Assigned permissions only"));
    toolbar.append(search, filterLabel);
    const summary = element("p", "permission-count"); summary.setAttribute("aria-live", "polite");
    const bulkNotice = element("p", "permission-bulk-notice"); bulkNotice.setAttribute("role", "status");
    const list = element("div", "permission-groups");
    const empty = element("p", "permission-empty", de ? "Keine passenden Berechtigungen gefunden." : "No matching permissions found.");
    const technicalLabel = element("label", "permission-technical-label");
    const technical = element("input"); technical.type = "checkbox";
    technicalLabel.append(technical, document.createTextNode(de ? "Technische Kennungen anzeigen" : "Show technical identifiers"));
    root.append(intro, superuser, toolbar, summary, bulkNotice, list, empty, technicalLabel);
    const groups = new Map();
    const rows = [];
    let inherited = new Map();
    let updatePresetPreview = () => {};
    let resetPresetUndo = () => {};
    const syncSelection = () => {
      options.forEach((option, id) => { option.selected = own.has(id); });
      select.dispatchEvent(new Event("change", {bubbles:true}));
      update();
    };
    const bulkControls = (members, category = null) => {
      const bar = element("div", "permission-bulk");
      bar.setAttribute("role", "group");
      bar.setAttribute("aria-label", category
        ? (de ? `Sammelauswahl: ${category}` : `Bulk selection: ${category}`)
        : (de ? "Sammelauswahl aller Bereiche" : "Bulk selection across categories"));
      const scope = element("p", "permission-bulk-scope");
      const actions = element("div", "permission-bulk-actions");
      const add = element("button", "button"); add.type = "button";
      const remove = element("button", "button"); remove.type = "button";
      actions.append(add, remove); bar.append(scope, actions);
      const apply = (checked) => {
        // Snapshot matches before changing the selection: the assigned filter may
        // hide rows as soon as their direct permissions are removed.
        const targets = members.filter(({row, permission}) => !row.hidden && own.has(permission.id) !== checked);
        targets.forEach(({permission}) => {
          if (checked) own.add(permission.id); else own.delete(permission.id);
        });
        resetPresetUndo();
        bulkNotice.textContent = de
          ? `${targets.length} direkte Rechte ${checked ? "ausgewählt" : "abgewählt"}. Noch nicht gespeichert.`
          : `${targets.length} direct permissions ${checked ? "selected" : "deselected"}. Not saved yet.`;
        syncSelection();
      };
      add.addEventListener("click", () => apply(true));
      remove.addEventListener("click", () => apply(false));
      return {bar, apply, update: () => {
        const matches = members.filter(({row}) => !row.hidden);
        const selected = matches.filter(({permission}) => own.has(permission.id)).length;
        const filtered = Boolean(search.value.trim()) || assigned.checked;
        scope.textContent = de
          ? (filtered ? `${matches.length} Treffer${category ? " in diesem Bereich" : ""} · Andere Rechte bleiben unverändert.`
            : category ? `${matches.length} Rechte in diesem Bereich` : `${matches.length} Rechte in allen Bereichen · Auch zugeklappte Bereiche werden berücksichtigt.`)
          : (filtered ? `${matches.length} matches${category ? " in this category" : ""} · Other permissions stay unchanged.`
            : category ? `${matches.length} permissions in this category` : `${matches.length} permissions across all categories · Includes collapsed categories.`);
        if (data.direct) scope.textContent += de ? " Gruppenrechte bleiben erhalten." : " Inherited permissions are retained.";
        const addLabel = de ? (filtered ? "Treffer auswählen" : category ? "Bereich auswählen" : "Alle auswählen")
          : (filtered ? "Select matches" : category ? "Select category" : "Select all");
        const removeLabel = de ? (filtered ? "Treffer abwählen" : category ? "Bereich abwählen" : "Alle abwählen")
          : (filtered ? "Deselect matches" : category ? "Deselect category" : "Deselect all");
        add.textContent = `${addLabel} (${matches.length - selected})`;
        remove.textContent = `${removeLabel} (${selected})`;
        add.disabled = matches.length === selected;
        remove.disabled = selected === 0;
        return {total: matches.length, selected};
      }};
    };
    const bulk = bulkControls(rows);
    root.insertBefore(bulk.bar, bulkNotice);
    permissions.forEach((permission) => {
      if (!groups.has(permission.category)) {
        const container = element("div", "permission-category-shell");
        const detail = element("details", "permission-category");
        const heading = element("summary");
        const categoryName = element("span", "permission-category-name", permission.category);
        const count = element("span", "permission-category-count");
        const members = [];
        const categoryBulk = bulkControls(members, permission.category);
        // Keep selection separate from disclosure, including when collapsed.
        // Sibling controls avoid nesting an interactive checkbox inside summary.
        const toggle = element("label", "permission-category-toggle vCheckboxLabel");
        const checkbox = element("input"); checkbox.type = "checkbox";
        checkbox.addEventListener("change", () => categoryBulk.apply(checkbox.checked));
        toggle.append(checkbox);
        heading.append(categoryName, count); detail.append(heading, categoryBulk.bar);
        container.append(toggle, detail); list.append(container);
        groups.set(permission.category, {container, detail, count, checkbox, toggle, rows: members, bulk: categoryBulk});
      }
      const group = groups.get(permission.category);
      const row = element("label", "permission-row");
      const checkbox = element("input"); checkbox.type = "checkbox"; checkbox.checked = own.has(permission.id);
      checkbox.setAttribute("aria-label", permission.title);
      const body = element("span", "permission-body");
      const top = element("span", "permission-row-title");
      const title = element("strong", "", permission.title);
      const kinds = de ? {read:"Anzeigen",change:"Ändern",action:"Aktion",access:"Zugriff"} : {read:"Read",change:"Change",action:"Action",access:"Access"};
      const kind = element("span", "permission-kind", kinds[permission.kind]);
      top.append(title, kind);
      if (permission.sensitive) top.append(element("span", "permission-sensitive", de ? "Weitreichendes Recht" : "Sensitive access"));
      const description = element("span", "permission-description", permission.description);
      const source = element("span", "permission-source");
      const code = element("code", "permission-code", permission.code);
      body.append(top, description, source, code); row.append(checkbox, body); group.detail.append(row);
      const record = {row, checkbox, permission, source, text: `${permission.title} ${permission.description} ${permission.code}`.toLocaleLowerCase()};
      rows.push(record); group.rows.push(record);
      checkbox.addEventListener("change", () => {
        if (checkbox.checked) own.add(permission.id); else own.delete(permission.id);
        options.get(permission.id).selected = checkbox.checked;
        select.dispatchEvent(new Event("change", {bubbles:true}));
        update();
      });
    });
    const update = () => {
      const needle = search.value.trim().toLocaleLowerCase();
      const allAccess = Boolean(document.getElementById("id_is_superuser")?.checked);
      let visible = 0;
      rows.forEach(({row, checkbox, permission, source, text}) => {
        checkbox.checked = own.has(permission.id);
        const via = inherited.get(permission.id) || [];
        row.hidden = !text.includes(needle) || (assigned.checked && !allAccess && !own.has(permission.id) && !via.length);
        if (!row.hidden) visible++;
        source.textContent = via.length ? (de ? "Über Gruppe: " : "Via group: ") + via.join(", ") : "";
        source.hidden = !via.length;
      });
      groups.forEach(({container, detail, count, checkbox, toggle, rows: members, bulk: categoryBulk}, category) => {
        container.hidden = !members.some(({row}) => !row.hidden);
        const selected = members.filter(({permission}) => own.has(permission.id) || inherited.has(permission.id)).length;
        count.textContent = `${selected} / ${members.length}`;
        if (needle || assigned.checked) detail.open = !container.hidden;
        const selection = categoryBulk.update();
        checkbox.checked = selection.total > 0 && selection.selected === selection.total;
        checkbox.indeterminate = selection.selected > 0 && selection.selected < selection.total;
        checkbox.disabled = selection.total === 0;
        const filtered = Boolean(needle) || assigned.checked;
        checkbox.setAttribute("aria-label", de
          ? `${filtered ? "Gefilterte" : "Alle"}${data.direct ? " direkten" : ""} Rechte in „${category}“`
          : `${filtered ? "Matching" : "All"}${data.direct ? " direct" : ""} permissions in “${category}”`);
        toggle.title = de
          ? `${checkbox.checked ? "Abwählen" : "Auswählen"}: ${selection.total} ${filtered ? "Treffer" : "Rechte"}${data.direct ? " · Gruppenrechte bleiben erhalten" : ""}`
          : `${checkbox.checked ? "Deselect" : "Select"}: ${selection.total} ${filtered ? "matches" : "permissions"}${data.direct ? " · Inherited permissions are retained" : ""}`;
      });
      bulk.update();
      const effective = new Set([...own, ...inherited.keys()]);
      summary.textContent = de ? `${own.size} direkt · ${inherited.size} über Gruppen · ${effective.size} wirksam · ${visible} Treffer` : `${own.size} direct · ${inherited.size} via groups · ${effective.size} effective · ${visible} matches`;
      if (!data.direct) summary.textContent = de ? `${own.size} ausgewählt · ${visible} Treffer` : `${own.size} selected · ${visible} matches`;
      else if (allAccess) summary.textContent = de ? `Alle Rechte durch Administrator-Status · ${own.size} zusätzlich direkt · ${visible} Treffer` : `All permissions through superuser status · ${own.size} also assigned directly · ${visible} matches`;
      if (data.direct && document.getElementById("id_is_active")?.checked === false) summary.textContent = de ? `Konto deaktiviert · ${effective.size} Rechte zugewiesen · ${visible} Treffer` : `Account inactive · ${effective.size} permissions assigned · ${visible} matches`;
      empty.hidden = visible > 0;
      superuser.hidden = !allAccess;
      updatePresetPreview();
    };
    const updateInherited = () => {
      const chosen = document.getElementById("id_groups_to");
      const original = document.getElementById("id_groups");
      // Django filters the displayed options, but its cache retains membership.
      const selectedGroups = new Set(Array.from(window.SelectBox?.cache?.id_groups_to || chosen?.options || original?.selectedOptions || [], option => String(option.value)));
      inherited = new Map();
      data.groups.filter(group => selectedGroups.has(group.id)).forEach(group => group.permissions.forEach(id => {
        if (!options.has(id)) return;
        inherited.set(id, [...(inherited.get(id) || []), group.name]);
      }));
      update();
    };
    if (!data.direct && data.presets?.length) {
      const block = element("div", "permission-presets");
      const title = element("h3", "", de ? "Mit einer Rolle starten" : "Start with a role");
      const help = element("p", "permission-intro", de
        ? "1. Vorlage wählen. 2. Mit „Vorlage übernehmen“ die Rechte auswählen. 3. Das Formular sichern. Du kannst mehrere Vorlagen kombinieren und jedes Recht einzeln anpassen."
        : "1. Choose a preset. 2. Select its permissions with “Apply preset”. 3. Save the form. You can combine presets and adjust every permission individually.");
      const label = element("label", "permission-preset-label", de ? "Rollenvorlage" : "Role preset");
      const chooser = element("select", "permission-preset-select"); chooser.id = select.id + "_preset";
      label.htmlFor = chooser.id;
      chooser.append(new Option(de ? "Vorlage auswählen …" : "Choose a preset …", ""));
      data.presets.forEach(preset => chooser.append(new Option(`${preset.title} · ${preset.permissions.length} ${de ? "Rechte" : "permissions"}`, preset.id)));
      const preview = element("div", "permission-preset-preview"); preview.hidden = true;
      const state = element("p", "permission-preset-state"); state.setAttribute("role", "status");
      const description = element("p", "permission-preset-description");
      const counts = element("p", "permission-count"); counts.setAttribute("aria-live", "polite");
      const impact = element("p", "permission-preset-impact", de
        ? "Vorhandene Rechte bleiben erhalten. Die Vorlage vergibt weder Vollzugriff noch Administrationszugang. Erst „Sichern“ speichert die Gruppenrechte."
        : "Existing permissions are retained. Presets do not enable superuser or staff status. Group permissions only take effect after saving the form.");
      const review = element("details", "permission-preset-review");
      const reviewTitle = element("summary"); const reviewList = element("ul");
      review.append(reviewTitle, reviewList);
      const actions = element("div", "permission-preset-actions");
      const apply = element("button", "button permission-preset-apply"); apply.type = "button";
      const undo = element("button", "button", de ? "Letzte Vorlage zurücknehmen" : "Undo last preset"); undo.type = "button"; undo.hidden = true;
      const notice = element("p", "permission-preset-notice"); notice.setAttribute("role", "status");
      actions.append(apply, undo); preview.append(state, description, counts, impact, review, actions, notice);
      block.append(title, help, label, chooser, preview); root.insertBefore(block, toolbar);
      let selectedPreset = null;
      let lastAdded = [];
      resetPresetUndo = () => { lastAdded = []; notice.textContent = ""; };
      updatePresetPreview = () => {
        if (!selectedPreset) return;
        const ids = selectedPreset.permissions.filter(id => options.has(id));
        const add = ids.filter(id => !own.has(id)).length;
        state.textContent = add
          ? (de ? "Vorschau · Vorlage noch nicht vollständig übernommen" : "Preview · Preset not fully applied yet")
          : (de ? "Alle Rechte dieser Vorlage sind im Formular ausgewählt" : "All permissions from this preset are selected in the form");
        state.dataset.complete = String(add === 0);
        counts.textContent = de ? `${add} zu ergänzen · ${ids.length - add} bereits ausgewählt` : `${add} to add · ${ids.length - add} already selected`;
        apply.textContent = add ? (de ? `Vorlage übernehmen (${add} neue Rechte)` : `Apply preset (${add} new permissions)`) : (de ? "Vollständig ausgewählt" : "Fully selected");
        apply.disabled = add === 0;
        const remaining = lastAdded.filter(id => own.has(id)).length;
        undo.hidden = lastAdded.length === 0;
        undo.disabled = remaining === 0;
      };
      chooser.addEventListener("change", () => {
        selectedPreset = data.presets.find(preset => preset.id === chooser.value) || null;
        preview.hidden = !selectedPreset;
        if (!selectedPreset) return;
        description.textContent = selectedPreset.description;
        reviewTitle.textContent = de ? `Enthaltene Rechte anzeigen (${selectedPreset.permissions.length})` : `Review included permissions (${selectedPreset.permissions.length})`;
        reviewList.replaceChildren();
        permissions.filter(permission => selectedPreset.permissions.includes(permission.id)).forEach(permission => {
          const item = element("li");
          item.append(element("strong", "", permission.title), element("span", "", permission.description));
          reviewList.append(item);
        });
        review.open = false;
        updatePresetPreview();
      });
      apply.addEventListener("click", () => {
        if (!selectedPreset) return;
        bulkNotice.textContent = "";
        lastAdded = selectedPreset.permissions.filter(id => options.has(id) && !own.has(id));
        lastAdded.forEach(id => own.add(id));
        notice.textContent = de ? `„${selectedPreset.title}“ übernommen: ${lastAdded.length} Rechte ergänzt. Jetzt „Sichern“, um die Gruppenrechte zu speichern.` : `Applied “${selectedPreset.title}”: added ${lastAdded.length} permissions. Save the form to store the group permissions.`;
        syncSelection();
      });
      undo.addEventListener("click", () => {
        bulkNotice.textContent = "";
        lastAdded.forEach(id => own.delete(id));
        lastAdded = [];
        notice.textContent = de ? "Ergänzung zurückgenommen. Vorher vorhandene Rechte bleiben erhalten." : "Preset addition undone. Previously selected permissions are retained.";
        syncSelection();
      });
    }
    search.addEventListener("input", update);
    assigned.addEventListener("change", update);
    technical.addEventListener("change", () => root.classList.toggle("show-permission-codes", technical.checked));
    document.getElementById("id_is_superuser")?.addEventListener("change", update);
    document.getElementById("id_is_active")?.addEventListener("change", update);
    const groupField = document.querySelector(".field-groups");
    if (groupField) {
      groupField.addEventListener("change", updateInherited);
      new MutationObserver(updateInherited).observe(groupField, {childList:true, subtree:true});
    }
    select.after(root); select.hidden = true; select.dataset.enhanced = "true";
    updateInherited();
  });
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", initialize);
  else initialize();
})();
