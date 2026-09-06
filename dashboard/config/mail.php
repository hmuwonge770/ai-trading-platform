<?php

return [
    'default' => env('MAIL_MAILER', 'log'),
    'mailers' => [
        'log' => ['transport' => 'log', 'channel' => env('LOG_CHANNEL', 'stack')],
    ],
    'from' => [
        'address' => env('MAIL_FROM_ADDRESS', 'dashboard@example.test'),
        'name' => env('MAIL_FROM_NAME', 'AI Trading Control'),
    ],
];
