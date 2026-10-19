<?php
// Fail before touching a database if the bundled PHP is incompatible.
$required = ['pgsql', 'curl', 'dom', 'fileinfo', 'gd', 'iconv', 'intl', 'mbstring',
    'openssl', 'simplexml', 'soap', 'sodium', 'xml', 'xmlreader', 'zip', 'zlib'];
foreach ($required as $extension) {
    if (!extension_loaded($extension)) {
        fwrite(STDERR, "Required PHP extension missing: {$extension}\n");
        exit(1);
    }
}
if (PHP_VERSION_ID < 80100 || PHP_VERSION_ID >= 80400 || PHP_INT_SIZE !== 8) {
    fwrite(STDERR, "This Moodle package requires 64-bit PHP 8.1-8.3.\n");
    exit(1);
}
$key = openssl_pkey_new(['private_key_bits' => 2048, 'private_key_type' => OPENSSL_KEYTYPE_RSA]);
if ($key === false) {
    fwrite(STDERR, "OpenSSL key generation is unavailable.\n");
    exit(1);
}
echo 'PHP runtime ready: ' . PHP_VERSION . "\n";
