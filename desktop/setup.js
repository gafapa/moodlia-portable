const copy = {
  en: {
    title: 'Create your local Moodle', intro: 'Choose a version and the tools you want to use. Everything is installed on this computer.',
    versionTitle: 'Moodle version', versionLabel: 'Version to install',
    versionHelp: 'Use the same version as your school when possible. This choice belongs to this workspace.',
    pluginsTitle: 'Optional plugins', moodliaDescription: 'Connect your AI assistant and automate Moodle tasks.',
    pluginsHelp: 'You can install Moodle on its own. Course formats must also be available on the destination Moodle when transferring courses.',
    account: 'Your administrator account will be teacher. Its password is created automatically and saved in your workspace.',
    cancel: 'Cancel', install: 'Install Moodle', installing: 'Preparing installation…',
    tabs: 'Show course topics as tabs.', unavailable: 'Available for Moodle 4.5, 5.0 and 5.1. Not offered for this version.',
    loadError: 'Setup could not load. Close the app and reopen it to try again.',
    installError: 'Installation could not start. Check the selected version and try again.',
  },
  es: {
    title: 'Crea tu Moodle local', intro: 'Elige la versión y las herramientas que quieres usar. Todo se instala en este ordenador.',
    versionTitle: 'Versión de Moodle', versionLabel: 'Versión que se instalará',
    versionHelp: 'Si puedes, usa la misma versión que tu centro. Esta elección corresponde a este espacio de trabajo.',
    pluginsTitle: 'Complementos opcionales', moodliaDescription: 'Conecta tu asistente de IA y automatiza tareas de Moodle.',
    pluginsHelp: 'Puedes instalar solo Moodle. Para trasladar cursos, el Moodle de destino también necesita los formatos de curso utilizados.',
    account: 'Tu cuenta de administrador será teacher. La contraseña se crea automáticamente y se guarda en tu espacio de trabajo.',
    cancel: 'Cancelar', install: 'Instalar Moodle', installing: 'Preparando la instalación…',
    tabs: 'Muestra los temas del curso como pestañas.', unavailable: 'Disponible para Moodle 4.5, 5.0 y 5.1. No se ofrece para esta versión.',
    loadError: 'No se ha podido cargar la configuración. Cierra la aplicación y vuelve a abrirla para reintentar.',
    installError: 'No se ha podido iniciar la instalación. Comprueba la versión seleccionada y vuelve a intentarlo.',
  },
};
const locale = navigator.language.startsWith('es') ? 'es' : 'en';
const text = copy[locale];
document.documentElement.lang = locale;
for (const element of document.querySelectorAll('[data-copy]')) element.textContent = text[element.dataset.copy];
document.title = text.title;
const version = document.getElementById('moodle-version');
const install = document.getElementById('install');
const status = document.getElementById('setup-status');
let plugins = {};

function updateCompatibility() {
  const branch = version.value.split('.').slice(0, 2).join('.');
  for (const [component, plugin] of Object.entries(plugins)) {
    const input = document.getElementById(component);
    const unavailable = !plugin.versions.includes(branch);
    input.disabled = unavailable;
    if (unavailable) input.checked = false;
    input.closest('label').classList.toggle('unavailable', unavailable);
    document.getElementById(`${component}-compatibility`).textContent = unavailable ? text.unavailable : '';
  }
}

async function loadCatalog() {
  try {
    const catalog = await window.portableSetup.catalog();
    if (!Array.isArray(catalog.versions) || !catalog.versions.length) throw new Error('Missing versions');
    plugins = catalog.plugins;
    for (const item of catalog.versions) {
      const option = document.createElement('option');
      option.value = item;
      option.textContent = `Moodle ${item}`;
      version.append(option);
    }
    for (const [component, plugin] of Object.entries(plugins)) {
      const label = document.createElement('label');
      label.className = 'plugin-option';
      label.htmlFor = component;
      const input = document.createElement('input');
      input.type = 'checkbox';
      input.id = component;
      input.setAttribute('aria-describedby', `${component}-compatibility`);
      const content = document.createElement('span');
      const name = document.createElement('strong');
      name.textContent = plugin.name;
      const description = document.createElement('span');
      description.className = 'description';
      description.textContent = text.tabs;
      const compatibility = document.createElement('span');
      compatibility.className = 'compatibility';
      compatibility.id = `${component}-compatibility`;
      compatibility.setAttribute('aria-live', 'polite');
      content.append(name, description, compatibility);
      label.append(input, content);
      document.getElementById('optional-plugins').append(label);
    }
    version.disabled = false;
    updateCompatibility();
    install.disabled = false;
    version.focus();
  } catch {
    status.textContent = text.loadError;
  }
}
version.addEventListener('change', updateCompatibility);
document.getElementById('cancel').addEventListener('click', async () => {
  try { await window.portableSetup.cancel(); } catch { status.textContent = text.loadError; }
});
document.getElementById('setup-form').addEventListener('submit', async event => {
  event.preventDefault();
  install.disabled = true;
  install.textContent = text.installing;
  status.textContent = '';
  try {
    await window.portableSetup.start({ version: version.value,
      moodlia: document.getElementById('moodlia-plugin').checked,
      plugins: Object.keys(plugins).filter(component => {
        const input = document.getElementById(component);
        return input.checked && !input.disabled;
      }),
    });
  } catch {
    install.disabled = false;
    install.textContent = text.install;
    status.textContent = text.installError;
  }
});
loadCatalog();
