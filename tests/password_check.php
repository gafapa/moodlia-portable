<?php
// Diagnostic boolean only: never print the password or its stored hash.
define('CLI_SCRIPT', true);
require($argv[1] . '/config.php');
$settings = json_decode(file_get_contents(getenv('MOODLIA_PRIVATE_CONFIG')), true, 512, JSON_THROW_ON_ERROR);
$teacher = $DB->get_record('user', ['username' => 'teacher'], '*', MUST_EXIST);
echo json_encode(['password_matches' => validate_internal_user_password($teacher, $settings['password']),
    'confirmed' => (bool)$teacher->confirmed, 'suspended' => (bool)$teacher->suspended], JSON_THROW_ON_ERROR) . "\n";
