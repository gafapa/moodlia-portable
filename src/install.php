<?php
// Pass generated credentials internally instead of exposing them in process arguments.
$settings = json_decode(file_get_contents(getenv('MOODLIA_PRIVATE_CONFIG')), true, 512, JSON_THROW_ON_ERROR);
$moodleroot = $argv[1];
$connection = pg_connect('postgresql://moodlia:' . rawurlencode($settings['database_password'])
    . '@127.0.0.1:' . (int)$settings['database_port'] . '/moodle');
if (!$connection) {
    throw new RuntimeException('Cannot inspect installation state.');
}
$table = pg_fetch_result(pg_query($connection, "SELECT to_regclass('public.mdl_config')"), 0, 0);
if ($table) {
    $result = pg_query($connection, "SELECT value FROM mdl_config WHERE name = 'version'");
    if ($result && pg_num_rows($result) === 1) {
        echo "Existing Moodle installation retained.\n";
        pg_close($connection);
        // Resume missing plugin installation after an interrupted first launch.
        $argv = [__FILE__, '--non-interactive'];
        $_SERVER['argv'] = $argv;
        $argc = count($argv);
        require($moodleroot . '/admin/cli/upgrade.php');
        exit(0);
    }
    throw new RuntimeException('An incomplete Moodle schema exists. Preserve the workspace before recovery.');
}
pg_close($connection);
$argv = [__FILE__, '--agree-license', '--adminuser=teacher', '--adminpass=' . $settings['password'],
    '--adminemail=teacher@example.invalid', '--fullname=MoodlIA Portable', '--shortname=MoodlIA Portable'];
$_SERVER['argv'] = $argv;
$argc = count($argv);
require($moodleroot . '/admin/cli/install_database.php');
