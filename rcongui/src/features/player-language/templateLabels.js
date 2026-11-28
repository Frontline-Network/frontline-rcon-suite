export function templateLabel(template, t) {
  const tr = key => t(`playerLanguages.${key}`, { defaultValue: t('playerLanguages.unnamedTemplate') });
  if (template.title?.trim()) return template.title;
  const [area, module, ...parts] = template.key.split('.');
  if (area === 'automod') {
    const action = parts.join('_');
    return `${tr(`modules.${module}`)} · ${tr(`actions.${action}`)}`;
  }
  if (area === 'autobalancer') return tr(`balanceLabels.${module}`);
  if (area === 'messages') return tr(`messageLabels.${module}`);
  return tr('unnamedTemplate');
}

export function templateSection(template, t) {
  const tr = key => t(`playerLanguages.${key}`, { defaultValue: t('playerLanguages.unnamedTemplate') });
  if (template.group === 'automod') return `${tr('automod')} · ${tr(`modules.${template.key.split('.')[1]}`)}`;
  return tr(template.group);
}

export function translationStatus(template) {
  if (template.needs_review) return 'needsReview';
  if (!template.source?.trim()) return 'unused';
  return ['de', 'en', 'fr'].every(code => template.translations?.[code]?.trim()) ? 'ready' : 'incomplete';
}
