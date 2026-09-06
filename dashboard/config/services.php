<?php

return [
    'trading_api' => [
        'url' => env('TRADING_API_URL', 'http://127.0.0.1:8000'),
        'environment' => env('TRADING_ENVIRONMENT', 'paper'),
        'enabled' => env('TRADING_ENABLED', false),
    ],
];
