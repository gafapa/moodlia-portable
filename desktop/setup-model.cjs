const branchOf = version => String(version).split('.').slice(0, 2).join('.');

function validateSelection(selection, versions, plugins) {
  if (!selection || !versions.includes(selection.version) || typeof selection.moodlia !== 'boolean'
      || !Array.isArray(selection.plugins) || selection.plugins.some(item => typeof item !== 'string')
      || new Set(selection.plugins).size !== selection.plugins.length) {
    throw new Error('Choose a bundled Moodle version and valid plugin options.');
  }
  for (const component of selection.plugins) {
    if (!Object.hasOwn(plugins, component) || !plugins[component].versions.includes(branchOf(selection.version))) {
      throw new Error('The selected plugin is unavailable for this Moodle version.');
    }
  }
  return { version: selection.version, moodlia: selection.moodlia, plugins: [...selection.plugins] };
}

module.exports = { branchOf, validateSelection };
