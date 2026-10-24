<?php
// Read back selected optional plugin installation without changing Moodle data.
define('CLI_SCRIPT', true);
require($argv[1] . '/config.php');
$settings = json_decode(file_get_contents(getenv('MOODLIA_PRIVATE_CONFIG')), true, 512, JSON_THROW_ON_ERROR);
foreach ($settings['optional_plugins'] ?? [] as $component) {
    $info = core_plugin_manager::instance()->get_plugin_info($component);
    if (!$info || !$info->versiondb || $info->versiondb != $info->versiondisk) {
        throw new RuntimeException('Selected plugin installation is incomplete: ' . $component);
    }
}
echo "Selected plugin versions agree on disk and in the database.\n";
