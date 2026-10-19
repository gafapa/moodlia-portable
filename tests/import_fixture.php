<?php
// Validate a native backup restored into a separate plugin-free synthetic Moodle.
define('CLI_SCRIPT', true);
require($argv[1] . '/config.php');
$page = $DB->get_record('page', ['name' => 'Portable page']);
if (!$page) {
    fwrite(STDERR, json_encode(['courses' => array_values($DB->get_records('course', null, 'id', 'id, shortname, fullname')),
        'pages' => array_values($DB->get_records('page', null, 'id', 'id,course,name'))]) . "\n");
    throw new RuntimeException('Restored synthetic page is missing.');
}
$course = $DB->get_record('course', ['id' => $page->course], '*', MUST_EXIST);
if (!str_contains($page->content, 'á é ñ') || get_config('local_moodlia', 'version')) {
    throw new RuntimeException('Restored content or plugin-free destination check failed.');
}
echo json_encode(['course_id' => (int)$course->id, 'page_id' => (int)$page->id,
    'content_preserved' => true, 'destination_plugin_installed' => false,
    'restored_shortname' => $course->shortname], JSON_THROW_ON_ERROR) . "\n";
