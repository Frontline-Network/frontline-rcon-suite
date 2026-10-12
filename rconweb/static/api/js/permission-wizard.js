/* Guided role setup. Draft answers never change Django's field until Apply. */
(() => {
  const el = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text) node.textContent = text;
    return node;
  };
  const mount = ({data, permissions, available, getOwn, apply, form, fieldId}) => {
    const de = data.german, t = (a, b) => de ? a : b;
    const planner = window.CRCONPermissionPlanner;
    const catalog = new Map(permissions.map(p => [p.id, p]));
    const root = el('section', 'permission-wizard');
    root.setAttribute('aria-label', t('Geführte Rolleneinrichtung', 'Guided role setup'));
    let sections = new Set(), answers = {}, position = 0, applied = false;
    let reviewSnapshot = '', feedback = '', appliedSummary = [];
    const steps = () => data.wizardSections.filter(s => sections.has(s.id))
      .flatMap(s => s.workflows).map(id => data.workflows.find(w => w.id === id));
    const draft = () => !applied && Object.values(answers).some(a => a.mode !== 'keep');
    const signature = () => JSON.stringify([...getOwn()].sort());
    const plan = () => planner.wizardPlan(data.workflows, answers, getOwn(), available);
    const modeText = mode => ({keep:t('Unverändert', 'Unchanged'), none:t('Kein Zugriff aus dieser Rolle', 'No access from this role'), read:t('Nur ansehen', 'View only'), custom:t('Ansehen und ausgewählte Aktionen', 'View and selected actions')})[mode];
    const button = (text, handler, className = '') => {
      const node = el('button', `button ${className}`, text); node.type = 'button';
      node.addEventListener('click', handler); return node;
    };
    const go = target => { position = target; feedback = ''; render(true); };
    const render = (focus = false) => {
      root.replaceChildren();
      if (applied) {
        const done = el('h3', '', t('Die Auswahl ist übernommen – jetzt speichern', 'Selection applied — now save'));
        done.tabIndex = -1;
        root.append(done, el('p', 'permission-wizard-lead', t('Deine Antworten stehen jetzt im Formular. Klicke unten auf „Sichern“, damit die Rolle für ihre Mitglieder gespeichert wird.', 'Your answers are now in the form. Choose “Save” below to store the role for its members.')));
        const summary = el('ul'); appliedSummary.forEach(text => summary.append(el('li', '', text))); root.append(summary);
        root.append(button(t('Weitere Bereiche einrichten', 'Set up more areas'), () => { applied = false; go(0); }));
        if (focus) done.focus();
        return;
      }
      const questions = steps(), last = questions.length + 1;
      const progress = el('p', 'permission-wizard-progress', position === 0
        ? t('Schritt 1 · Aufgaben auswählen', 'Step 1 · Choose responsibilities')
        : t(`Schritt ${position + 1} von ${last + 1}`, `Step ${position + 1} of ${last + 1}`));
      const heading = el('h3', '', position === 0 ? t('Welche Aufgaben soll die Rolle übernehmen?', 'What should this role be responsible for?')
        : position === last ? t('Passt diese Rolle so?', 'Does this role look right?')
        : t(`Was darf die Rolle bei „${questions[position - 1].title}“?`, `What may this role do in “${questions[position - 1].title}”?`));
      heading.tabIndex = -1;
      root.append(progress, heading);
      if (feedback) { const alert = el('p', 'permission-wizard-warning', feedback); alert.setAttribute('role', 'alert'); root.append(alert); }
      const navigation = el('div', 'permission-wizard-navigation');
      if (position === 0) {
        root.append(el('p', 'permission-wizard-lead', t(
          'Wähle die Bereiche, die du einrichten möchtest. Wir fragen dich anschließend einzeln, was erlaubt sein soll, und erklären die Folgen. Technische Rechte musst du nicht kennen.',
          'Choose the areas you want to set up. We will ask what to allow, one area at a time, and explain the effects. You do not need to know technical permission names.')));
        root.append(el('p', 'permission-wizard-note', t(
          'Bestehende Rolle? „Unverändert“ lässt ihre Auswahl zunächst stehen. Gemeinsam genutzte Rechte können mehrere Bereiche betreffen; die Zusammenfassung zeigt solche Auswirkungen. Bis zur Übernahme bleibt alles ein Entwurf.',
          'Editing an existing role? “Unchanged” initially keeps its selection. Shared permissions can affect multiple areas; the review shows these effects. Nothing changes until you apply the draft.')));
        const cards = el('div', 'permission-wizard-sections');
        const next = button(t('Einrichtung starten', 'Start setup'), () => go(1), 'permission-wizard-primary');
        next.disabled = sections.size === 0;
        data.wizardSections.forEach(section => {
          const label = el('label', 'permission-wizard-option');
          const checkbox = el('input'); checkbox.type = 'checkbox'; checkbox.checked = sections.has(section.id);
          checkbox.setAttribute('aria-label', section.title);
          const body = el('span'); body.append(el('strong', '', section.title), el('small', '', section.description));
          checkbox.addEventListener('change', () => {
            if (checkbox.checked) sections.add(section.id);
            else { sections.delete(section.id); section.workflows.forEach(id => delete answers[id]); }
            applied = false; next.disabled = sections.size === 0;
          });
          label.append(checkbox, body); cards.append(label);
        });
        root.append(cards);
        navigation.append(next);
        if (Object.keys(answers).length) navigation.append(button(t('Entwurf verwerfen', 'Discard draft'), () => { answers = {}; sections = new Set(); applied = false; go(0); }));
      } else if (position < last) {
        const workflow = questions[position - 1];
        const answer = answers[workflow.id] || {mode:'keep', actions:[]};
        answers[workflow.id] = answer;
        const ids = new Set(workflow.bundles.flatMap(b => b.permissions));
        const ownCount = [...ids].filter(id => getOwn().has(id)).length;
        root.append(el('p', 'permission-wizard-lead', workflow.explanation));
        root.append(el('p', 'permission-wizard-note', ownCount
          ? t('Diese Rolle hat hier bereits Rechte. Wähle bewusst, ob du sie behalten, einschränken oder erweitern möchtest.', 'This role already has permissions here. Choose whether to keep, restrict or extend them.')
          : t('Diese Rolle vergibt hier bisher keine Rechte.', 'This role currently grants no permissions here.')));
        const choices = el('fieldset', 'permission-wizard-choices');
        choices.append(el('legend', '', t('Zugriff für diesen Bereich', 'Access to this area')));
        const modes = [
          ['keep', t('Die aktuelle Auswahl nicht gezielt ändern.', 'Do not intentionally change the current selection.')],
          ['none', t('Die zugehörigen Rechte aus dieser Rolle entfernen. Andere Gruppen können weiterhin Zugriff geben.', 'Remove the related permissions from this role. Other groups may still grant access.')],
          ['read', t('Informationen ansehen, aber keine Einstellungen ändern oder Maßnahmen ausführen. Vorhandene Aktionsrechte dieses Bereichs werden entfernt.', 'View information without changing settings or taking action. Existing action permissions in this area will be removed.')],
          ...(workflow.bundles.length > 1 ? [['custom', t('Zusätzlich genau die Aktionen erlauben, die du unten auswählst. Nicht ausgewählte Aktionen dieses Bereichs werden entfernt.', 'Also allow exactly the actions selected below. Unselected actions in this area will be removed.')]] : []),
        ];
        modes.forEach(([mode, description]) => {
          const label = el('label', 'permission-wizard-option');
          const radio = el('input'); radio.type = 'radio'; radio.name = `${fieldId}_wizard_access`; radio.value = mode; radio.checked = answer.mode === mode;
          const body = el('span'); body.append(el('strong', '', modeText(mode)), el('small', '', description));
          radio.setAttribute('aria-label', modeText(mode));
          radio.addEventListener('change', () => { answer.mode = mode; applied = false; render(); root.querySelector(`input[value="${mode}"]`)?.focus(); });
          label.append(radio, body); choices.append(label);
        });
        root.append(choices);
        if (answer.mode === 'custom') {
          const actions = el('fieldset', 'permission-wizard-actions');
          actions.append(el('legend', '', t('Welche Aktionen soll die Rolle ausführen dürfen?', 'Which actions should this role be allowed to perform?')));
          root.append(el('p', 'permission-wizard-note', t('Nur angehakte Aktionen sind erlaubt. Ohne Auswahl bleibt es beim Ansehen.', 'Only checked actions are allowed. With none selected, access stays view-only.')));
          workflow.bundles.slice(1).forEach(bundle => {
            const label = el('label', 'permission-wizard-option');
            const checkbox = el('input'); checkbox.type = 'checkbox'; checkbox.checked = answer.actions.includes(bundle.id);
            checkbox.setAttribute('aria-label', bundle.title);
            const body = el('span'); body.append(el('strong', '', bundle.title));
            const extra = bundle.permissions.filter(id => !workflow.bundles[0].permissions.includes(id));
            extra.forEach(id => { const p = catalog.get(id); if (p) body.append(el('small', '', p.description)); });
            if (bundle.sensitive) body.append(el('small', 'permission-wizard-risk', t('Weitreichende Befugnis: nur vertrauenswürdigen Personen geben.', 'Sensitive access: grant only to trusted people.')));
            checkbox.addEventListener('change', () => { answer.actions = checkbox.checked ? [...answer.actions, bundle.id] : answer.actions.filter(id => id !== bundle.id); applied = false; });
            label.append(checkbox, body); actions.append(label);
          });
          root.append(actions);
        }
        if (workflow.bundles[0].sensitive) root.append(el('p', 'permission-wizard-warning', t('Schon das Ansehen kann hier Zugangsdaten oder technische Verbindungsinformationen offenlegen.', 'Even viewing this area can expose credentials or technical connection details.')));
        const explain = el('details', 'permission-wizard-details');
        explain.append(el('summary', '', t('Was wird beim Ansehen freigeschaltet?', 'What does view access include?')));
        const list = el('ul'); workflow.bundles[0].permissions.forEach(id => { if (catalog.has(id)) list.append(el('li', '', catalog.get(id).description)); });
        explain.append(list); root.append(explain);
        navigation.append(button(t('Zurück', 'Back'), () => go(position - 1)), button(position === last - 1 ? t('Zusammenfassung prüfen', 'Review role') : t('Weiter', 'Next'), () => go(position + 1), 'permission-wizard-primary'));
      } else {
        const proposal = plan(); reviewSnapshot = signature();
        const blocked = proposal.conflicts.length || proposal.unavailable.length || proposal.invalid.length;
        root.append(el('p', 'permission-wizard-lead', t('Prüfe deine Antworten. „In die Rolle übernehmen“ aktualisiert nur das Formular. Erst „Sichern“ speichert die Rolle für ihre Mitglieder.', 'Review your answers. “Apply to role” updates only the form. “Save” stores the role for its members.')));
        const list = el('div', 'permission-wizard-review');
        questions.forEach((workflow, index) => {
          const answer = answers[workflow.id] || {mode:'keep', actions:[]};
          const row = el('div'); const body = el('div');
          body.append(el('strong', '', workflow.title), el('p', '', modeText(answer.mode)));
          if (answer.mode === 'custom') {
            const names = workflow.bundles.filter(b => answer.actions.includes(b.id)).map(b => b.title);
            body.append(el('small', '', names.length ? names.join(' · ') : t('Keine zusätzlichen Aktionen', 'No additional actions')));
          }
          row.append(body, button(t('Ändern', 'Edit'), () => go(index + 1))); list.append(row);
        });
        root.append(list);
        proposal.conflicts.forEach(conflict => root.append(el('p', 'permission-wizard-warning', t(
          `Diese Antworten widersprechen sich: „${conflict.allow.join(', ')}“ benötigt ein Recht, das bei „${conflict.deny.join(', ')}“ entzogen werden soll (${catalog.get(conflict.id)?.title || conflict.id}). Bitte die Antworten anpassen.`,
          `These answers conflict: “${conflict.allow.join(', ')}” needs a permission denied in “${conflict.deny.join(', ')}” (${catalog.get(conflict.id)?.title || conflict.id}). Please adjust your answers.`))));
        if (proposal.unavailable.length || proposal.invalid.length) root.append(el('p', 'permission-wizard-warning', t('Die benötigten Rechte stehen nicht vollständig zur Verfügung. Dieser Entwurf kann nicht übernommen werden. Bitte die Expertenansicht oder den Support verwenden.', 'Some required permissions are unavailable. This draft cannot be applied. Please use the expert view or contact support.')));
        if (proposal.affected.length) root.append(el('p', 'permission-wizard-warning', t(
          `Gemeinsam genutzte Rechte ändern auch die Auswahl in: ${proposal.affected.map(w => w.title).join(', ')}. Diese Bereiche wurden nicht eigens geändert. Prüfe diese Auswirkungen vor der Übernahme.`,
          `Shared permissions also change the selection in: ${proposal.affected.map(w => w.title).join(', ')}. These areas were not edited separately. Review these effects before applying.`)));
        const delta = el('details', 'permission-wizard-details');
        delta.append(el('summary', '', t(`Rechte: ${proposal.added.length} ergänzen · ${proposal.removed.length} entfernen`, `Permissions: add ${proposal.added.length} · remove ${proposal.removed.length}`)));
        const deltaList = el('ul');
        [[proposal.added, t('Ergänzen', 'Add')], [proposal.removed, t('Entfernen', 'Remove')]].forEach(([ids, verb]) => ids.forEach(id => deltaList.append(el('li', '', `${verb}: ${catalog.get(id)?.title || id}`))));
        delta.append(deltaList); root.append(delta);
        const touched = new Set(data.workflows.flatMap(w => w.bundles.flatMap(b => b.permissions)));
        const outside = [...getOwn()].filter(id => !touched.has(id));
        if (outside.length) {
          const preserved = el('details', 'permission-wizard-details');
          preserved.append(el('summary', '', t(`Weitere unveränderte Rechte (${outside.length})`, `Other unchanged permissions (${outside.length})`)));
          const values = el('ul'); outside.forEach(id => values.append(el('li', '', catalog.get(id)?.title || id))); preserved.append(values); root.append(preserved);
        }
        root.append(el('p', 'permission-wizard-note', t('Rechte aus weiteren Rollen addieren sich. „Kein Zugriff“ hier kann Rechte aus anderen Gruppen oder Vollzugriff nicht aufheben. Benutzerverwaltung und interne Systemrechte vergibt der Assistent nicht.', 'Permissions from other roles add together. “No access” here cannot override another group or superuser access. This wizard does not grant user-management or internal system permissions.')));
        const acknowledgement = el('input'); acknowledgement.type = 'checkbox';
        const label = el('label', 'permission-wizard-confirm');
        label.append(acknowledgement, document.createTextNode(t('Ich habe die Änderungen und ihre Auswirkungen auf die Mitglieder dieser Rolle geprüft.', 'I have reviewed the changes and their effects on members of this role.')));
        const changed = proposal.added.length + proposal.removed.length > 0;
        const accept = button(t('In die Rolle übernehmen', 'Apply to role'), () => {
          if (!acknowledgement.checked) return;
          if (signature() !== reviewSnapshot) { feedback = t('Die Rechte im Formular haben sich geändert. Bitte die aktualisierte Zusammenfassung erneut prüfen.', 'The form permissions changed. Please review the updated summary.'); render(true); return; }
          const fresh = plan();
          if (fresh.conflicts.length || fresh.unavailable.length || fresh.invalid.length) { render(true); return; }
          appliedSummary = questions.map(w => `${w.title}: ${modeText(answers[w.id]?.mode || 'keep')}`);
          apply(fresh.next); applied = true; answers = {}; sections = new Set(); position = 0;
          feedback = ''; render(true);
        }, 'permission-wizard-primary');
        accept.disabled = true;
        acknowledgement.addEventListener('change', () => { accept.disabled = !acknowledgement.checked || Boolean(blocked) || !changed; });
        if (changed) root.append(label);
        else root.append(el('p', 'permission-wizard-note', t('Es sind keine Änderungen an der aktuellen Auswahl nötig.', 'No changes to the current selection are needed.')));
        navigation.append(button(t('Zurück', 'Back'), () => go(position - 1)), accept);
        navigation.append(button(t('Entwurf verwerfen', 'Discard draft'), () => { answers = {}; sections = new Set(); applied = false; go(0); }));
      }
      root.append(navigation);
      if (position > 0 && position < last) root.append(el('p', 'permission-wizard-note', t('Deine Antworten sind noch ein Entwurf. Du kannst zurückgehen; gespeichert wird jetzt noch nichts.', 'Your answers are still a draft. You can go back; nothing is saved yet.')));
      if (focus) heading.focus();
    };
    form?.addEventListener('submit', event => {
      if (!draft()) return;
      event.preventDefault(); feedback = t('Der Assistent enthält noch einen Entwurf. Bitte zuerst die Zusammenfassung prüfen und übernehmen oder den Entwurf verwerfen.', 'The wizard still contains a draft. Review and apply it first, or discard the draft.');
      position = steps().length + 1; render(true);
    });
    render(); return root;
  };
  window.CRCONPermissionWizard = {mount};
})();
