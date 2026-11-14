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
    const de = data.german, fr = data.language === "fr", t = (a, b, c) => de ? a : fr ? (c || window.CRCONPermissionFrench?.[b] || b) : b;
    const own = new Set(Array.from(select.selectedOptions, (option) => option.value));
    const initial = new Set(own);
    const planner = window.CRCONPermissionPlanner;
    // If a static asset fails, retain Django's native, fully functional select.
    if (!planner) return;
    const options = new Map(Array.from(select.options, (option) => [option.value, option]));
    const permissions = data.permissions.filter((item) => options.has(item.id));
    // Keep the native select as Django's source of truth, including popup additions.
    const groupSelect = document.querySelector("select.crcon-group-select");
    if (groupSelect && !groupSelect.dataset.enhanced) {
      const groupRoot = element("section", "crcon-group-picker");
      groupRoot.setAttribute("aria-label", t("Gruppen auswählen", "Choose groups"));
      const groupIntro = element("p", "permission-intro", t("Alle Rechte der ausgewählten Gruppen gelten für dieses Konto. Einzelne Rechte kannst du darunter ergänzen.", "This account inherits every permission from its selected groups. Add individual permissions below."));
      const groupSearch = element("input"); groupSearch.type = "search";
      groupSearch.placeholder = t("Gruppen suchen …", "Search groups …");
      groupSearch.setAttribute("aria-label", t("Gruppen durchsuchen", "Search groups"));
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
          if (count !== undefined) body.append(element("small", "", t(`${count} Berechtigungen`, `${count} permissions`, `${count} autorisations`)));
          checkbox.addEventListener("change", () => {
            option.selected = checkbox.checked;
            groupSelect.dispatchEvent(new Event("change", {bubbles:true}));
          });
          label.append(checkbox, body); groupList.append(label);
        });
        if (!matches) groupList.append(element("p", "permission-empty", t("Keine passenden Gruppen gefunden.", "No matching groups found.")));
        updateGroupCount();
      };
      const updateGroupCount = () => {
        const n = groupSelect.selectedOptions.length;
        groupCount.textContent = t(`${n} ${n === 1 ? "Gruppe" : "Gruppen"} ausgewählt · Änderungen werden mit dem Formular gespeichert.`, `${n} ${n === 1 ? "group" : "groups"} selected · Changes are saved with the form.`, `${n} groupe(s) sélectionné(s) · Les modifications sont enregistrées avec le formulaire.`);
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
        const label = t("Gruppe anlegen", "Create group");
        addGroup.append(document.createTextNode(label)); addGroup.setAttribute("aria-label", label);
      }
    }
    const root = element("section", "permission-picker");
    root.setAttribute("aria-label", t("Berechtigungen auswählen", "Choose permissions"));
    const intro = element("p", "permission-intro", data.direct
      ? (t("Direkte Rechte ergänzen die Rechte aus den ausgewählten Gruppen. Gruppenrechte können hier nicht entzogen werden.", "Direct permissions add to the selected groups. Group permissions cannot be revoked here."))
      : (t("Diese Rechte gelten für alle Mitglieder der Gruppe. Rechte mehrerer Gruppen ergänzen sich. Wähle eine Aufgabe oder Rollenvorlage und prüfe die Änderungen vor dem Sichern.", "These permissions apply to all group members. Permissions from multiple groups add together. Choose a task or role preset and review the changes before saving.")));
    const superuser = element("p", "permission-superuser", t("Administrator-Status ist aktiv: Dieses Konto besitzt alle Rechte. Die Einzelauswahl schränkt diese Vollrechte nicht ein.", "Superuser status is active: this account has all permissions. Individual selections do not restrict that access."));
    const toolbar = element("div", "permission-toolbar");
    const search = element("input"); search.type = "search";
    search.placeholder = t("Rechte suchen, z. B. kicken, Karten, VIP …", "Search permissions, e.g. kick, maps, VIP …");
    search.setAttribute("aria-label", t("Berechtigungen durchsuchen", "Search permissions"));
    const filterLabel = element("label", "permission-assigned-label");
    const assigned = element("input"); assigned.type = "checkbox";
    filterLabel.append(assigned, document.createTextNode(t("Nur vergebene Rechte", "Assigned permissions only")));
    toolbar.append(search, filterLabel);
    const kindFilter = element("select", "permission-kind-filter");
    kindFilter.setAttribute("aria-label", t("Rechte nach Wirkung filtern", "Filter permissions by effect"));
    [["all", t("Alle Rechte", "All permissions")], ["read", t("Nur anzeigen", "View only")], ["write", t("Ändern & Aktionen", "Changes & actions")]]
      .forEach(([value, label]) => kindFilter.append(new Option(label, value)));
    toolbar.append(kindFilter);
    const summary = element("p", "permission-count"); summary.setAttribute("aria-live", "polite");
    const bulkNotice = element("p", "permission-bulk-notice"); bulkNotice.setAttribute("role", "status");
    const list = element("div", "permission-groups");
    const empty = element("p", "permission-empty", t("Keine passenden Berechtigungen gefunden.", "No matching permissions found."));
    const technicalLabel = element("label", "permission-technical-label");
    const technical = element("input"); technical.type = "checkbox";
    technicalLabel.append(technical, document.createTextNode(t("Technische Kennungen anzeigen", "Show technical identifiers")));
    const internalLabel = element("label", "permission-assigned-label");
    const internal = element("input"); internal.type = "checkbox";
    internalLabel.append(internal, document.createTextNode(t("Interne Systemrechte einblenden", "Show internal system permissions")));
    const internalHelp = element("p", "permission-internal-help", t("Interne Django-Rechte sind für Support und Spielermoderation nicht nötig. Bereits vergebene interne Rechte bleiben sichtbar und werden nicht automatisch entfernt.", "Internal Django permissions are not needed for support or player moderation. Existing assignments remain visible and are never removed automatically."));
    const pending = element("details", "permission-pending");
    const pendingTitle = element("summary");
    const pendingList = element("ul");
    const reset = element("button", "button", data.direct ? (t("Änderungen an direkten Rechten zurücknehmen", "Undo direct-permission changes")) : (t("Auswahländerungen zurücknehmen", "Undo selection changes"))); reset.type = "button";
    pending.append(pendingTitle, pendingList, reset);
    root.append(intro, superuser, toolbar, summary, pending, bulkNotice, list, empty, internalLabel, internalHelp, technicalLabel);
    const groups = new Map();
    const rows = [];
    let inherited = new Map();
    let updatePresetPreview = () => {};
    let resetPresetUndo = () => {};
    let updateWorkflow = () => {};
    let clearWorkflowNotice = () => {};
    const syncSelection = () => {
      options.forEach((option, id) => { option.selected = own.has(id); });
      select.dispatchEvent(new Event("change", {bubbles:true}));
      update();
    };
    const bulkControls = (members, category = null) => {
      const bar = element("div", "permission-bulk");
      bar.setAttribute("role", "group");
      bar.setAttribute("aria-label", category
        ? (t(`Sammelauswahl: ${category}`, `Bulk selection: ${category}`, `Sélection multiple : ${category}`))
        : (t("Sammelauswahl aller Bereiche", "Bulk selection across categories")));
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
          : fr ? `${targets.length} autorisations directes ${checked ? "sélectionnées" : "désélectionnées"}. Pas encore enregistré.` : `${targets.length} direct permissions ${checked ? "selected" : "deselected"}. Not saved yet.`;
        syncSelection();
      };
      add.addEventListener("click", () => apply(true));
      remove.addEventListener("click", () => apply(false));
      return {bar, apply, update: () => {
        const matches = members.filter(({row}) => !row.hidden);
        const selected = matches.filter(({permission}) => own.has(permission.id)).length;
        const filtered = Boolean(search.value.trim()) || assigned.checked || kindFilter.value !== "all" || !internal.checked;
        scope.textContent = de
          ? (filtered ? `${matches.length} Treffer${category ? " in diesem Bereich" : ""} · Andere Rechte bleiben unverändert.`
            : category ? `${matches.length} Rechte in diesem Bereich` : `${matches.length} Rechte in allen Bereichen · Auch zugeklappte Bereiche werden berücksichtigt.`)
          : fr ? (filtered ? `${matches.length} résultat(s)${category ? " dans cette catégorie" : ""} · Les autres autorisations restent inchangées.` : category ? `${matches.length} autorisation(s) dans cette catégorie` : `${matches.length} autorisation(s) dans toutes les catégories · Les catégories repliées sont incluses.`)
          : (filtered ? `${matches.length} matches${category ? " in this category" : ""} · Other permissions stay unchanged.`
            : category ? `${matches.length} permissions in this category` : `${matches.length} permissions across all categories · Includes collapsed categories.`);
        if (data.direct) scope.textContent += t(" Gruppenrechte bleiben erhalten.", " Inherited permissions are retained.");
        const addLabel = de ? (filtered ? "Treffer auswählen" : category ? "Bereich auswählen" : "Alle auswählen")
          : fr ? (filtered ? "Sélectionner les résultats" : category ? "Sélectionner la catégorie" : "Tout sélectionner") : (filtered ? "Select matches" : category ? "Select category" : "Select all");
        const removeLabel = de ? (filtered ? "Treffer abwählen" : category ? "Bereich abwählen" : "Alle abwählen")
          : fr ? (filtered ? "Désélectionner les résultats" : category ? "Désélectionner la catégorie" : "Tout désélectionner") : (filtered ? "Deselect matches" : category ? "Deselect category" : "Deselect all");
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
      const kinds = de ? {read:"Anzeigen",change:"Ändern",action:"Aktion",access:"Zugriff"} : fr ? {read:"Consulter",change:"Modifier",action:"Action",access:"Accès"} : {read:"Read",change:"Change",action:"Action",access:"Access"};
      const kind = element("span", "permission-kind", kinds[permission.kind]);
      top.append(title, kind);
      if (permission.sensitive) top.append(element("span", "permission-sensitive", t("Weitreichendes Recht", "Sensitive access")));
      const description = element("span", "permission-description", permission.description);
      const source = element("span", "permission-source");
      const code = element("code", "permission-code", permission.code);
      body.append(top, description, source, code); row.append(checkbox, body); group.detail.append(row);
      const record = {row, checkbox, permission, source, text: `${permission.title} ${permission.description} ${permission.code} ${permission.aliases || ""} ${permission.category}`};
      rows.push(record); group.rows.push(record);
      checkbox.addEventListener("change", () => {
        resetPresetUndo();
        if (checkbox.checked) own.add(permission.id); else own.delete(permission.id);
        options.get(permission.id).selected = checkbox.checked;
        select.dispatchEvent(new Event("change", {bubbles:true}));
        update();
      });
    });
    const update = () => {
      clearWorkflowNotice();
      const needle = search.value.trim().toLocaleLowerCase();
      const allAccess = Boolean(document.getElementById("id_is_superuser")?.checked);
      let visible = 0;
      rows.forEach(({row, checkbox, permission, source, text}) => {
        checkbox.checked = own.has(permission.id);
        const via = inherited.get(permission.id) || [];
        row.hidden = !planner.matches(text, needle)
          || (permission.internal && !internal.checked && !own.has(permission.id) && !via.length)
          || (kindFilter.value === "read" && permission.kind !== "read")
          || (kindFilter.value === "write" && permission.kind === "read")
          || (assigned.checked && !allAccess && !own.has(permission.id) && !via.length);
        if (!row.hidden) visible++;
        source.textContent = via.length ? (t("Über Gruppe: ", "Via group: ")) + via.join(", ") : "";
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
        const filtered = Boolean(needle) || assigned.checked || kindFilter.value !== "all" || !internal.checked;
        checkbox.setAttribute("aria-label", de
          ? `${filtered ? "Gefilterte" : "Alle"}${data.direct ? " direkten" : ""} Rechte in „${category}“`
          : fr ? `${filtered ? "Autorisations correspondantes" : "Toutes les autorisations"}${data.direct ? " directes" : ""} dans « ${category} »` : `${filtered ? "Matching" : "All"}${data.direct ? " direct" : ""} permissions in “${category}”`);
        toggle.title = de
          ? `${checkbox.checked ? "Abwählen" : "Auswählen"}: ${selection.total} ${filtered ? "Treffer" : "Rechte"}${data.direct ? " · Gruppenrechte bleiben erhalten" : ""}`
          : fr ? `${checkbox.checked ? "Désélectionner" : "Sélectionner"} : ${selection.total} ${filtered ? "résultat(s)" : "autorisation(s)"}${data.direct ? " · Les autorisations héritées sont conservées" : ""}` : `${checkbox.checked ? "Deselect" : "Select"}: ${selection.total} ${filtered ? "matches" : "permissions"}${data.direct ? " · Inherited permissions are retained" : ""}`;
      });
      bulk.update();
      const effective = new Set([...own, ...inherited.keys()]);
      summary.textContent = t(`${own.size} direkt · ${inherited.size} über Gruppen · ${effective.size} wirksam · ${visible} Treffer`, `${own.size} direct · ${inherited.size} via groups · ${effective.size} effective · ${visible} matches`, `${own.size} directes · ${inherited.size} par groupes · ${effective.size} effectives · ${visible} résultats`);
      if (!data.direct) summary.textContent = t(`${own.size} ausgewählt · ${visible} Treffer`, `${own.size} selected · ${visible} matches`, `${own.size} sélectionnées · ${visible} résultats`);
      else if (allAccess) summary.textContent = t(`Alle Rechte durch Administrator-Status · ${own.size} zusätzlich direkt · ${visible} Treffer`, `All permissions through superuser status · ${own.size} also assigned directly · ${visible} matches`, `Toutes les autorisations par le statut superutilisateur · ${own.size} directes en plus · ${visible} résultats`);
      if (data.direct && document.getElementById("id_is_active")?.checked === false) summary.textContent = t(`Konto deaktiviert · ${effective.size} Rechte zugewiesen · ${visible} Treffer`, `Account inactive · ${effective.size} permissions assigned · ${visible} matches`, `Compte désactivé · ${effective.size} autorisations attribuées · ${visible} résultats`);
      empty.hidden = visible > 0;
      superuser.hidden = !allAccess;
      const delta = planner.changes(initial, own);
      pending.hidden = delta.added.length + delta.removed.length === 0;
      pendingTitle.textContent = t(`Noch nicht gespeichert: ${delta.added.length} ergänzt · ${delta.removed.length} entfernt`, `Not saved: ${delta.added.length} added · ${delta.removed.length} removed`, `Non enregistré : ${delta.added.length} ajoutées · ${delta.removed.length} retirées`);
      pendingList.replaceChildren();
      for (const [ids, prefix] of [[delta.added, t("Ergänzt", "Added")], [delta.removed, t("Entfernt", "Removed")]]) {
        ids.forEach(id => pendingList.append(element("li", "", `${prefix}: ${permissions.find(p => p.id === id)?.title || options.get(id)?.textContent || id}`)));
      }
      updatePresetPreview();
      updateWorkflow(allAccess);
    };
    reset.addEventListener("click", () => {
      own.clear(); initial.forEach(id => own.add(id));
      resetPresetUndo(); bulkNotice.textContent = ""; syncSelection();
    });
    if (data.workflows?.length) {
      const block = element("section", "permission-workflows");
      block.setAttribute("aria-label", t("Rechte nach Aufgabe", "Permissions by task"));
      const heading = element("h3", "", data.direct ? (t("Was soll das Konto können?", "What should this account be able to do?")) : (t("Was soll die Rolle können?", "What should this role be able to do?")));
      const help = element("p", "permission-intro", t("Wähle einen Bereich. „Anzeigen“ bündelt die dazugehörigen Leserechte. Zusätzliche Aktionen werden separat freigegeben. Es wird nichts automatisch ausgewählt.", "Choose an area. “View” bundles the related read permissions. Additional actions are granted separately. Nothing is selected automatically."));
      const chooser = element("select", "permission-workflow-select");
      chooser.setAttribute("aria-label", t("Aufgabe auswählen", "Choose a task"));
      chooser.append(new Option(t("Aufgabe auswählen …", "Choose a task …"), ""));
      data.workflows.forEach(workflow => chooser.append(new Option(workflow.title, workflow.id)));
      const preview = element("div", "permission-workflow-preview");
      const notice = element("p", "permission-bulk-notice"); notice.setAttribute("role", "status");
      clearWorkflowNotice = () => { notice.textContent = ""; };
      block.append(heading, help, chooser, preview, notice);
      root.insertBefore(block, toolbar);
      let bundleRows = [];
      chooser.addEventListener("change", () => {
        preview.replaceChildren(); bundleRows = []; notice.textContent = "";
        const workflow = data.workflows.find(item => item.id === chooser.value);
        if (!workflow) return;
        workflow.bundles.forEach(bundle => {
          const panel = element("div", "permission-bundle");
          const title = element("h4", "", bundle.title);
          const state = element("p", "permission-bundle-state");
          const review = element("details", "permission-preset-review");
          review.open = bundle.kind === "read" && bundle.permissions.length <= 12;
          review.append(element("summary", "", t(`Enthaltene Rechte prüfen (${bundle.permissions.length})`, `Review included permissions (${bundle.permissions.length})`, `Vérifier les autorisations incluses (${bundle.permissions.length})`)));
          const requirements = element("ul"); review.append(requirements);
          const apply = element("button", "button"); apply.type = "button";
          const actionLabel = `${workflow.title}: ${bundle.title}`;
          panel.append(title, state);
          if (bundle.kind !== "read") panel.append(element("p", "permission-intro", t("Enthält auch die Leserechte dieses Bereichs. Änderungen und Aktionen können den Spielbetrieb beeinflussen.", "Also includes this area's read permissions. Changes and actions can affect the game server.")));
          if (bundle.sensitive) panel.append(element("p", "permission-sensitive", t("Weitreichendes Recht – Umfang vor dem Übernehmen prüfen.", "Sensitive access – review the scope before applying.")));
          panel.append(review, apply); preview.append(panel);
          bundleRows.push({bundle, state, apply, requirements, actionLabel});
          apply.addEventListener("click", () => {
            const access = Boolean(document.getElementById("id_is_superuser")?.checked);
            const plan = planner.bundleState(bundle, own, inherited, options, access);
            if (plan.unavailable.length || !plan.missing.length) return;
            plan.missing.forEach(id => own.add(id)); resetPresetUndo();
            syncSelection();
            notice.textContent = t(`${plan.missing.length} ${plan.missing.length === 1 ? "Recht" : "Rechte"} ergänzt. Noch nicht gespeichert; bitte die Änderungen prüfen und das Formular sichern.`, `Added ${plan.missing.length} ${plan.missing.length === 1 ? "permission" : "permissions"}. Not saved yet; review the changes and save the form.`, `${plan.missing.length} autorisation(s) ajoutée(s). Pas encore enregistré ; vérifiez les modifications et enregistrez le formulaire.`);
          });
        });
        update();
      });
      updateWorkflow = (allAccess) => bundleRows.forEach(({bundle, state, apply, requirements, actionLabel}) => {
        const plan = planner.bundleState(bundle, own, inherited, options, allAccess);
        state.textContent = plan.unavailable.length
          ? (t("Nicht vollständig verfügbar – keine automatische Teilfreigabe.", "Not fully available – partial access cannot be applied."))
          : plan.complete
          ? (t("Im Formular vollständig", "Complete in this form"))
          : (t(`${bundle.permissions.length - plan.missing.length} von ${bundle.permissions.length} Rechten vorhanden · ${plan.missing.length} ${plan.missing.length === 1 ? "fehlt" : "fehlen"}`, `${bundle.permissions.length - plan.missing.length} of ${bundle.permissions.length} permissions assigned · ${plan.missing.length} missing`, `${bundle.permissions.length - plan.missing.length} autorisation(s) sur ${bundle.permissions.length} attribuée(s) · ${plan.missing.length} manquante(s)`));
        state.dataset.complete = String(plan.complete);
        apply.textContent = plan.complete ? (t("Bereits zugewiesen", "Already assigned")) : (t(`Fehlende Rechte ergänzen (${plan.missing.length})`, `Add missing permissions (${plan.missing.length})`, `Ajouter les autorisations manquantes (${plan.missing.length})`));
        apply.setAttribute("aria-label", `${actionLabel}: ${apply.textContent}`);
        apply.disabled = plan.complete || plan.unavailable.length > 0;
        requirements.replaceChildren();
        bundle.permissions.forEach(id => {
          const permission = permissions.find(p => p.id === id);
          if (!permission) return;
          const via = inherited.get(id) || [];
          const status = allAccess ? (t("Vollzugriff", "Superuser")) : own.has(id) ? (t("ausgewählt", "selected")) : via.length ? (t(`über Gruppe: ${via.join(", ")}`, `via group: ${via.join(", ")}`, `par le groupe : ${via.join(", ")}`)) : (t("fehlt", "missing"));
          requirements.append(element("li", "", `${permission.title} — ${status}`));
        });
      });
    }
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
      const title = element("h3", "", t("Mit einer Rolle starten", "Start with a role"));
      const help = element("p", "permission-intro", t("1. Vorlage wählen. 2. Mit „Vorlage übernehmen“ die Rechte auswählen. 3. Das Formular sichern. Du kannst mehrere Vorlagen kombinieren und jedes Recht einzeln anpassen.", "1. Choose a preset. 2. Select its permissions with “Apply preset”. 3. Save the form. You can combine presets and adjust every permission individually."));
      const label = element("label", "permission-preset-label", t("Rollenvorlage", "Role preset"));
      const chooser = element("select", "permission-preset-select"); chooser.id = select.id + "_preset";
      label.htmlFor = chooser.id;
      chooser.append(new Option(t("Vorlage auswählen …", "Choose a preset …"), ""));
      data.presets.forEach(preset => chooser.append(new Option(`${preset.title} · ${preset.permissions.length} ${t("Rechte", "permissions")}`, preset.id)));
      const preview = element("div", "permission-preset-preview"); preview.hidden = true;
      const state = element("p", "permission-preset-state"); state.setAttribute("role", "status");
      const description = element("p", "permission-preset-description");
      const counts = element("p", "permission-count"); counts.setAttribute("aria-live", "polite");
      const impact = element("p", "permission-preset-impact", t("Vorhandene Rechte bleiben erhalten. Die Vorlage vergibt weder Vollzugriff noch Administrationszugang. Erst „Sichern“ speichert die Gruppenrechte.", "Existing permissions are retained. Presets do not enable superuser or staff status. Group permissions only take effect after saving the form."));
      const review = element("details", "permission-preset-review");
      const reviewTitle = element("summary"); const reviewList = element("ul");
      review.append(reviewTitle, reviewList);
      const actions = element("div", "permission-preset-actions");
      const apply = element("button", "button permission-preset-apply"); apply.type = "button";
      const undo = element("button", "button", t("Letzte Vorlage zurücknehmen", "Undo last preset")); undo.type = "button"; undo.hidden = true;
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
          ? (t("Vorschau · Vorlage noch nicht vollständig übernommen", "Preview · Preset not fully applied yet"))
          : (t("Alle Rechte dieser Vorlage sind im Formular ausgewählt", "All permissions from this preset are selected in the form"));
        state.dataset.complete = String(add === 0);
        counts.textContent = t(`${add} zu ergänzen · ${ids.length - add} bereits ausgewählt`, `${add} to add · ${ids.length - add} already selected`, `${add} à ajouter · ${ids.length - add} déjà sélectionnée(s)`);
        apply.textContent = add ? (t(`Vorlage übernehmen (${add} neue Rechte)`, `Apply preset (${add} new permissions)`, `Appliquer le modèle (${add} nouvelle(s) autorisation(s))`)) : (t("Vollständig ausgewählt", "Fully selected"));
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
        reviewTitle.textContent = t(`Enthaltene Rechte anzeigen (${selectedPreset.permissions.length})`, `Review included permissions (${selectedPreset.permissions.length})`, `Vérifier les autorisations incluses (${selectedPreset.permissions.length})`);
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
        notice.textContent = t(`„${selectedPreset.title}“ übernommen: ${lastAdded.length} Rechte ergänzt. Jetzt „Sichern“, um die Gruppenrechte zu speichern.`, `Applied “${selectedPreset.title}”: added ${lastAdded.length} permissions. Save the form to store the group permissions.`, `« ${selectedPreset.title} » appliqué : ${lastAdded.length} autorisation(s) ajoutée(s). Enregistrez le formulaire pour conserver les autorisations du groupe.`);
        syncSelection();
      });
      undo.addEventListener("click", () => {
        bulkNotice.textContent = "";
        lastAdded.forEach(id => own.delete(id));
        lastAdded = [];
        notice.textContent = t("Ergänzung zurückgenommen. Vorher vorhandene Rechte bleiben erhalten.", "Preset addition undone. Previously selected permissions are retained.");
        syncSelection();
      });
    }
    if (!data.direct && data.wizardSections?.length && window.CRCONPermissionWizard) {
      intro.textContent = t("Die Rolle bestimmt, was ihre Mitglieder dürfen. Der Assistent führt dich durch die Auswahl. Einzelrechte und Vorlagen findest du bei Bedarf in der Expertenansicht.", "This role controls what its members may do. The wizard guides you through setup. Individual permissions and presets remain available in the expert view.");
      const expert = element("details", "permission-expert");
      expert.append(element("summary", "", t("Expertenansicht: einzelne Rechte & Vorlagen", "Expert view: individual permissions & presets")));
      Array.from(root.children).filter(node => ![intro, superuser, pending].includes(node)).forEach(node => expert.append(node));
      const wizard = window.CRCONPermissionWizard.mount({data, permissions, available:options, getOwn:() => new Set(own), form:select.closest('form'), fieldId:select.id,
        apply: next => { own.clear(); next.forEach(id => own.add(id)); resetPresetUndo(); syncSelection(); }
      });
      root.insertBefore(wizard, pending); root.append(expert);
    }
    search.addEventListener("input", update);
    assigned.addEventListener("change", update);
    kindFilter.addEventListener("change", update);
    internal.addEventListener("change", update);
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
