<?php
// Read private settings dynamically so the stopped package can change folders.
unset($CFG);
global $CFG;
$CFG = new stdClass();
$privateconfig = getenv('MOODLIA_PRIVATE_CONFIG');
if (!$privateconfig) {
    throw new RuntimeException('Start Moodle using the MoodlIA Portable application.');
}
$workspace = dirname($privateconfig, 2);
$bundle = getenv('MOODLIA_RUNTIME_ROOT');
require_once($bundle . '/app/request.php');
$settings = json_decode(file_get_contents($privateconfig), true, 512, JSON_THROW_ON_ERROR);
$CFG->dbtype = 'pgsql';
$CFG->dblibrary = 'native';
$CFG->dbhost = '127.0.0.1';
$CFG->dbname = 'moodle';
$CFG->dbuser = 'moodlia';
$CFG->dbpass = $settings['database_password'];
$CFG->prefix = 'mdl_';
$CFG->dboptions = ['dbpersist' => false, 'dbport' => $settings['database_port'], 'dbsocket' => ''];
$CFG->wwwroot = 'http://127.0.0.1:' . $settings['http_port'];
$CFG->dataroot = $workspace . '/data/moodledata';
$CFG->admin = 'admin';
$CFG->directorypermissions = 0700;
$CFG->pathtophp = $bundle . '/runtime/php/php' . (PHP_OS_FAMILY === 'Windows' ? '.exe' : '');
$CFG->noemailever = true;
$CFG->disableupdateautodeploy = true;
require_once(__DIR__ . '/lib/setup.php');
