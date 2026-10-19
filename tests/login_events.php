<?php
// Inspect only synthetic authentication event metadata, never credentials.
define('CLI_SCRIPT', true);
require($argv[1] . '/config.php');
$events = $DB->get_records_select('logstore_standard_log', 'eventname = ? OR eventname = ?',
    ['\\core\\event\\user_login_failed', '\\core\\event\\user_loggedin'], 'id DESC', 'id,eventname,other', 0, 6);
echo json_encode(array_values($events), JSON_THROW_ON_ERROR) . "\n";
