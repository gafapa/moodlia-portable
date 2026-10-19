<?php
// Repair only the synthetic site used to exercise interrupted-install recovery.
define('CLI_SCRIPT', true);
require($argv[1] . '/config.php');
require_once($CFG->libdir . '/adminlib.php');
\core\session\manager::set_user(get_admin());
admin_apply_default_settings(null, true);
echo "Synthetic site defaults completed.\n";
