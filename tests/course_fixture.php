<?php
// Synthetic, local-only authoring fixture. Never run against a school server.
define('CLI_SCRIPT', true);
require($argv[1] . '/config.php');
require_once($CFG->dirroot . '/course/lib.php');
require_once($CFG->dirroot . '/course/modlib.php');
\core\session\manager::set_user(get_admin());
if (!get_config('core', 'portable_preservation_marker')) {
    set_config('portable_preservation_marker', 'synthetic-setting');
    set_config('frontpagecourselimit', 37);
}
if (get_config('core', 'frontpagecourselimit') != 37) {
    throw new RuntimeException('A user-modified site setting was overwritten.');
}
$course = $DB->get_record('course', ['shortname' => 'PORTABLE-EVIDENCE']);
if (!$course) {
    $course = create_course((object)[
        'fullname' => 'Portable authoring evidence', 'shortname' => 'PORTABLE-EVIDENCE',
        'category' => 1, 'format' => 'topics', 'numsections' => 2,
        'visible' => 0, 'summary' => '<p>Synthetic course for persistence and export checks.</p>',
        'summaryformat' => FORMAT_HTML]);
    add_moduleinfo((object)[
        'modulename' => 'page', 'module' => $DB->get_field('modules', 'id', ['name' => 'page']),
        'section' => 1, 'name' => 'Portable page', 'intro' => '', 'introformat' => FORMAT_HTML,
        'content' => '<p>Persist this synthetic page: á é ñ.</p>', 'contentformat' => FORMAT_HTML,
        'display' => 5, 'visible' => 1, 'visibleoncoursepage' => 1, 'cmidnumber' => '',
        'printintro' => 0, 'printlastmodified' => 0], $course);
}
$page = $DB->get_record('page', ['course' => $course->id, 'name' => 'Portable page'], '*', MUST_EXIST);
if (!str_contains($page->content, 'á é ñ')) {
    throw new RuntimeException('Page content was not preserved.');
}
echo json_encode(['course_id' => (int)$course->id, 'page_id' => (int)$page->id,
    'human_users' => $DB->count_records_select('user', 'deleted = 0 AND username <> ?', ['guest']),
    'teacher_is_admin' => is_siteadmin($DB->get_record('user', ['username' => 'teacher']))], JSON_THROW_ON_ERROR) . "\n";
