<?php
// Create the authoring database only when it does not already exist.
$settings = json_decode(file_get_contents(getenv('MOODLIA_PRIVATE_CONFIG')), true, 512, JSON_THROW_ON_ERROR);
$connection = pg_connect('postgresql://moodlia:' . rawurlencode($settings['database_password'])
    . '@127.0.0.1:' . (int)$settings['database_port'] . '/postgres');
if (!$connection) {
    throw new RuntimeException('Cannot connect to the bundled database.');
}
$result = pg_query($connection, "SELECT 1 FROM pg_database WHERE datname = 'moodle'");
if (!$result) {
    throw new RuntimeException('Cannot inspect the authoring database.');
}
if (pg_num_rows($result) === 0 && !pg_query($connection, "CREATE DATABASE moodle ENCODING 'UTF8' TEMPLATE template0")) {
    throw new RuntimeException('Cannot create the authoring database.');
}
pg_close($connection);
