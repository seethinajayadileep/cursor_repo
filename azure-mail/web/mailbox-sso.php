<?php
/**
 * Admin-panel jump into SOGo for one mailbox.
 * The brands panel signs a short-lived HMAC. This file never reads mailbox passwords.
 */
$fail = static function (): void {
    header('Location: /SOGo/', true, 302);
    exit;
};

$email = strtolower(trim((string) ($_GET['u'] ?? '')));
$ticket = trim((string) ($_GET['t'] ?? ''));
if ($email === '' || !filter_var($email, FILTER_VALIDATE_EMAIL) || $ticket === '') {
    $fail();
}

$key_file = __DIR__ . '/inc/.mailbox-sso.key';
if (!is_readable($key_file)) {
    $fail();
}
$secret = trim((string) file_get_contents($key_file));
if ($secret === '') {
    $fail();
}

$parts = explode('.', $ticket, 2);
if (count($parts) !== 2 || !ctype_digit($parts[0])) {
    $fail();
}
[$exp, $sig] = $parts;
if (time() > (int) $exp) {
    $fail();
}
$calc = hash_hmac('sha256', $email . '.' . $exp, $secret);
if (!is_string($sig) || !hash_equals($calc, $sig)) {
    $fail();
}

require_once $_SERVER['DOCUMENT_ROOT'] . '/inc/prerequisites.inc.php';

if (function_exists('user_get_alias_details') && user_get_alias_details($email) === false) {
    $fail();
}

if (function_exists('session_regenerate_id')) {
    session_regenerate_id(true);
}

$_SESSION['mailcow_cc_username'] = $email;
$_SESSION['mailcow_cc_role'] = 'user';
$_SESSION['sogo-sso-user-allowed'] = [$email];
$_SESSION['SESS_REMOTE_UA'] = $_SERVER['HTTP_USER_AGENT'] ?? '';
$_SESSION['LAST_ACTIVITY'] = time();
unset(
    $_SESSION['pending_pw_update'],
    $_SESSION['pending_tfa_setup'],
    $_SESSION['mailcow_cc_api'],
    $_SESSION['mailcow_cc_api_access']
);

if (function_exists('acl')) {
    acl('to_session');
}

if (isset($pdo) && $pdo instanceof PDO) {
    try {
        $stmt = $pdo->prepare(
            'REPLACE INTO sasl_log (`service`, `app_password`, `username`, `real_rip`)
             VALUES (\'SSO\', 0, :username, :remote_addr)'
        );
        $stmt->execute([
            ':username' => $email,
            ':remote_addr' => ($_SERVER['HTTP_X_REAL_IP'] ?? $_SERVER['REMOTE_ADDR'] ?? ''),
        ]);
    } catch (Throwable $e) {
        // Open SOGo even if the audit row cannot be written.
    }
}

header('Location: /SOGo/so/', true, 302);
exit;
