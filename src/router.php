<?php
// PHP's server handles PATH_INFO for Moodle file endpoints. Private data is outside its document root.
$path = rawurldecode(parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH) ?? '/');
if (preg_match('~(^|/)(\.|config\.php|vendor|node_modules)(/|$)|\x00~', $path)) {
    http_response_code(404);
    exit;
}
return false;
