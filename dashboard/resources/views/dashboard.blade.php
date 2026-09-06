<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>AI Trading Control</title>
    <style>
        :root { color-scheme: dark; font-family: Inter, ui-sans-serif, system-ui, sans-serif; }
        * { box-sizing: border-box; }
        body { margin: 0; min-height: 100vh; background: #090b10; color: #e8ecf3; }
        .shell { display: grid; grid-template-columns: 240px 1fr; min-height: 100vh; }
        aside { border-right: 1px solid #202530; padding: 28px 20px; background: #0d1016; }
        main { padding: 32px; max-width: 1500px; width: 100%; }
        .brand { font-weight: 800; letter-spacing: -.03em; font-size: 18px; margin-bottom: 38px; }
        nav a { display: block; padding: 10px 12px; border-radius: 9px; color: #8f99aa; text-decoration: none; margin: 4px 0; }
        nav a.active, nav a:hover { background: #171c25; color: #fff; }
        .eyebrow { color: #7f8a9d; text-transform: uppercase; font-size: 11px; letter-spacing: .12em; font-weight: 700; }
        h1 { font-size: clamp(28px, 4vw, 42px); margin: 8px 0 6px; letter-spacing: -.04em; }
        .sub { color: #8993a5; margin: 0 0 28px; }
        .grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 16px; }
        .card { background: #10141c; border: 1px solid #202530; border-radius: 14px; padding: 20px; }
        .label { color: #7f8a9d; font-size: 12px; margin-bottom: 10px; }
        .value { font-size: 24px; font-weight: 750; }
        .ok { color: #6ee7a8; } .warn { color: #f8c96b; } .bad { color: #ff7d8c; }
        .panel { margin-top: 16px; }
        .gate { display: flex; align-items: center; justify-content: space-between; padding: 14px 0; border-bottom: 1px solid #202530; }
        .gate:last-child { border-bottom: 0; }
        .pill { border: 1px solid #2c3442; border-radius: 999px; padding: 5px 10px; font-size: 11px; font-weight: 700; }
        .notice { margin-top: 16px; padding: 14px 16px; border-radius: 10px; background: #171c25; color: #aeb7c6; font-size: 13px; line-height: 1.5; }
        @media (max-width: 900px) { .shell { grid-template-columns: 1fr; } aside { border-right: 0; border-bottom: 1px solid #202530; } .grid { grid-template-columns: repeat(2, 1fr); } }
        @media (max-width: 560px) { main { padding: 20px; } .grid { grid-template-columns: 1fr; } }
    </style>
</head>
<body>
<div class="shell">
    <aside>
        <div class="brand">AI Trading Control</div>
        <nav>
            <a class="active" href="{{ route('dashboard') }}">Overview</a>
            <a href="#research">Research</a>
            <a href="#promotion">Promotion</a>
            <a href="#risk">Risk &amp; Safety</a>
            <a href="#operations">Operations</a>
        </nav>
    </aside>
    <main>
        <div class="eyebrow">Control plane</div>
        <h1>Trading operations</h1>
        <p class="sub">Research-first visibility over the deterministic trading lifecycle.</p>

        <section class="grid">
            <div class="card"><div class="label">Environment</div><div class="value">{{ strtoupper($environment) }}</div></div>
            <div class="card"><div class="label">Trading enabled</div><div class="value {{ $tradingEnabled ? 'warn' : 'ok' }}">{{ $tradingEnabled ? 'ENABLED' : 'DISABLED' }}</div></div>
            <div class="card"><div class="label">Control API</div><div class="value {{ $health['status'] === 'healthy' ? 'ok' : ($health['status'] === 'degraded' ? 'warn' : 'bad') }}">{{ strtoupper($health['status']) }}</div></div>
            <div class="card"><div class="label">Live posture</div><div class="value ok">FAIL-CLOSED</div></div>
        </section>

        <section class="card panel" id="promotion">
            <div class="eyebrow">Promotion gates</div>
            <div class="gate"><span>Production readiness</span><span class="pill ok">VERIFIED</span></div>
            <div class="gate"><span>Two-person authorization</span><span class="pill ok">REQUIRED</span></div>
            <div class="gate"><span>Live canary</span><span class="pill ok">GATED</span></div>
            <div class="gate"><span>Limited live</span><span class="pill ok">GATED</span></div>
            <div class="gate"><span>Full live</span><span class="pill ok">GATED</span></div>
        </section>

        <section class="card panel" id="risk">
            <div class="eyebrow">Safety boundary</div>
            <div class="gate"><span>Kill switch</span><span class="pill ok">FAIL-CLOSED</span></div>
            <div class="gate"><span>Circuit breaker</span><span class="pill ok">FAIL-CLOSED</span></div>
            <div class="gate"><span>Exchange credentials</span><span class="pill">NOT EXPOSED</span></div>
            <div class="gate"><span>Order submission</span><span class="pill">NOT FROM DASHBOARD</span></div>
        </section>

        <div class="notice">{{ $health['message'] }} The dashboard is a control and observability surface; live credentials and exchange order access remain outside the UI.</div>
    </main>
</div>
</body>
</html>
