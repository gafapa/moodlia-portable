<?php
// Idempotent bootstrap for this private, single-administrator authoring site.
define('CLI_SCRIPT', true);
require($argv[1] . '/config.php');
require_once($CFG->libdir . '/externallib.php');
$settings = json_decode(file_get_contents(getenv('MOODLIA_PRIVATE_CONFIG')), true, 512, JSON_THROW_ON_ERROR);
$bundle = dirname(getenv('MOODLIA_PRIVATE_CONFIG'), 2);
$initial = !is_file($bundle . '/data/installed.json');
$teacher = $DB->get_record('user', ['username' => 'teacher', 'deleted' => 0], '*', MUST_EXIST);
if (!is_siteadmin($teacher)) {
    throw new RuntimeException('The teacher account must be the site administrator.');
}
\core\session\manager::set_user($teacher);
require_once($CFG->dirroot . '/mod/lti/upgradelib.php');
if (mod_lti_verify_private_key() !== '') {
    throw new RuntimeException('The LTI signing key could not be generated.');
}
if ($initial) {
require_once($CFG->libdir . '/adminlib.php');
admin_apply_default_settings(null, true);
$site = get_site();
if (empty($site->fullname) || empty($site->shortname)) {
    $DB->set_field('course', 'fullname', 'MoodlIA Portable', ['id' => SITEID]);
    $DB->set_field('course', 'shortname', 'MoodlIA Portable', ['id' => SITEID]);
}
set_config('registrationpending', 0);
set_config('enablewebservices', 1);
set_config('webserviceprotocols', 'rest');
if ($settings['plugin_enabled']) {
    set_config('webmcp_enabled', 1, 'local_moodlia');
}
set_config('registerauth', '');
set_config('auth', 'manual');
set_config('enableguestlogin', 0);
set_config('guestloginbutton', 0);
set_config('backup_auto_active', 0);
}
$shortname = $settings['plugin_enabled'] ? 'local_moodlia' : 'portable_core';
$service = $DB->get_record('external_services', ['shortname' => $shortname]);
if (!$service && !$settings['plugin_enabled']) {
    $serviceid = $DB->insert_record('external_services', (object)[
        'name' => 'Portable Core authoring', 'shortname' => $shortname, 'enabled' => 1,
        'restrictedusers' => 1, 'requiredcapability' => '', 'component' => '',
        'timecreated' => time(), 'timemodified' => time(), 'downloadfiles' => 1, 'uploadfiles' => 1]);
    $service = $DB->get_record('external_services', ['id' => $serviceid], '*', MUST_EXIST);
    // The only human account is the local administrator. Core APIs retain their own checks.
    foreach ($DB->get_fieldset_select('external_functions', 'name', "name LIKE 'core_%' OR name LIKE 'mod_%'") as $name) {
        $DB->insert_record('external_services_functions', (object)[
            'externalserviceid' => $serviceid, 'functionname' => $name]);
    }
}
if (!$service) {
    throw new RuntimeException('MoodlIA external service is missing.');
}
if ($initial) {
    $service->enabled = 1;
    $service->restrictedusers = 1;
    $DB->update_record('external_services', $service);
}
if (!$DB->record_exists('external_services_users', ['externalserviceid' => $service->id, 'userid' => $teacher->id])) {
    $DB->insert_record('external_services_users', (object)[
        'externalserviceid' => $service->id, 'userid' => $teacher->id,
        'iprestriction' => '', 'validuntil' => 0, 'timecreated' => time()]);
}
$tokenfile = $bundle . '/connection/token.txt';
$token = is_file($tokenfile) ? trim(file_get_contents($tokenfile)) : '';
$existing = $token !== '' ? $DB->get_record('external_tokens', [
    'token' => $token, 'userid' => $teacher->id, 'externalserviceid' => $service->id]) : false;
if (!$existing || ($existing->validuntil && $existing->validuntil <= time())) {
    $arguments = [EXTERNAL_TOKEN_PERMANENT, $service, (int)$teacher->id, context_system::instance(), 0, ''];
    if (class_exists('core_external\\util') && method_exists('core_external\\util', 'generate_token')) {
        $token = \core_external\util::generate_token(...$arguments);
    } else {
        $token = external_generate_token(...$arguments);
    }
    $temporary = $tokenfile . '.tmp';
    file_put_contents($temporary, $token . "\n", LOCK_EX);
    chmod($temporary, 0600);
    if (!rename($temporary, $tokenfile)) {
        throw new RuntimeException('Cannot save connection token.');
    }
}
// A DB marker prevents partially installed sites from being reported as ready.
file_put_contents($bundle . '/data/installed.json', json_encode([
    'username' => 'teacher', 'moodle' => $CFG->release,
    'plugin' => get_config('local_moodlia', 'version')], JSON_PRETTY_PRINT) . "\n", LOCK_EX);
echo "API enabled for the teacher administrator.\n";
