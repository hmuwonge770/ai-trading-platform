<?php

namespace App\Http\Controllers;

use Illuminate\Http\Client\ConnectionException;
use Illuminate\Support\Facades\Http;
use Illuminate\View\View;

final class DashboardController extends Controller
{
    public function __invoke(): View
    {
        $apiUrl = rtrim((string) config('services.trading_api.url'), '/');
        $health = [
            'status' => 'unreachable',
            'message' => 'Control API health has not been checked.',
        ];

        if ($apiUrl !== '') {
            try {
                $response = Http::timeout(3)->get($apiUrl.'/health');
                $health = $response->successful()
                    ? ['status' => 'healthy', 'message' => 'FastAPI control service is reachable.']
                    : ['status' => 'degraded', 'message' => 'Control service returned HTTP '.$response->status().'.'];
            } catch (ConnectionException) {
                $health = ['status' => 'unreachable', 'message' => 'Control service is not reachable.'];
            }
        }

        return view('dashboard', [
            'health' => $health,
            'environment' => config('services.trading_api.environment', 'paper'),
            'tradingEnabled' => filter_var(config('services.trading_api.enabled', false), FILTER_VALIDATE_BOOL),
        ]);
    }
}
