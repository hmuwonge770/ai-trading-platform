<?php

namespace Tests\Feature;

use Tests\TestCase;

final class DashboardTest extends TestCase
{
    public function test_dashboard_renders(): void
    {
        $response = $this->get('/');

        $response->assertOk();
        $response->assertSee('AI Trading Control');
        $response->assertSee('FAIL-CLOSED');
        $response->assertSee('PAPER');
        $response->assertSee('DISABLED');
    }
}
