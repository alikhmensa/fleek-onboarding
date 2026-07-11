require('dotenv').config();
const express = require('express');
const cors    = require('cors');
const crypto  = require('crypto');
const { Resend } = require('resend');

const app     = express();
const PORT    = process.env.PORT    || 3001;
const APP_URL = process.env.APP_URL || 'http://localhost:8080';

app.use(cors({ origin: APP_URL }));
app.use(express.json());

const resend = new Resend(process.env.RESEND_API_KEY);

// In-memory token store: token -> { email, firstName, verified, expires }
const tokenStore = new Map();

// ── Clean up expired tokens every 10 min ───────────────
setInterval(() => {
  const now = Date.now();
  for (const [token, record] of tokenStore) {
    if (now > record.expires) tokenStore.delete(token);
  }
}, 10 * 60 * 1000);

// ──────────────────────────────────────────────────────
// POST /api/send-verification
// Body: { email, firstName }
// ──────────────────────────────────────────────────────
app.post('/api/send-verification', async (req, res) => {
  const { email, firstName = 'there' } = req.body;
  if (!email) return res.status(400).json({ error: 'Email is required' });

  // Invalidate any existing token for this email
  for (const [t, r] of tokenStore) {
    if (r.email === email) tokenStore.delete(t);
  }

  const token   = crypto.randomBytes(32).toString('hex');
  const expires = Date.now() + 24 * 60 * 60 * 1000; // 24 hours
  tokenStore.set(token, { email, firstName, verified: false, expires });

  const verifyUrl = `http://localhost:${PORT}/api/verify?token=${token}`;

  console.log(`\n📧 Sending verification email to ${email}`);
  console.log(`🔗 Verify URL: ${verifyUrl}\n`);

  try {
    const { data, error } = await resend.emails.send({
      from: 'Fleek Companion <onboarding@resend.dev>',
      to:   email,
      subject: '✅ Verify your Fleek Companion account',
      html: buildEmailHtml(firstName, verifyUrl),
    });

    if (error) {
      console.error('Resend error:', error);
      return res.status(500).json({ error: error.message });
    }

    console.log('✅ Email sent, id:', data.id);
    res.json({ success: true, message: 'Verification email sent' });
  } catch (err) {
    console.error('Failed to send email:', err.message);
    res.status(500).json({ error: err.message });
  }
});

// ──────────────────────────────────────────────────────
// GET /api/verify?token=xxx
// Called when user clicks the link in their email
// ──────────────────────────────────────────────────────
app.get('/api/verify', (req, res) => {
  const { token } = req.query;
  const record    = tokenStore.get(token);

  if (!record) {
    console.log('❌ Invalid token:', token);
    return res.redirect(`${APP_URL}?verified=false&reason=invalid`);
  }

  if (Date.now() > record.expires) {
    tokenStore.delete(token);
    console.log('❌ Expired token for:', record.email);
    return res.redirect(`${APP_URL}?verified=false&reason=expired`);
  }

  record.verified = true;
  console.log(`✅ Email verified for ${record.email}`);
  res.redirect(`${APP_URL}?verified=true&email=${encodeURIComponent(record.email)}`);
});

// ──────────────────────────────────────────────────────
// GET /api/check-verification?email=xxx
// Frontend polls this every 3 seconds while waiting
// ──────────────────────────────────────────────────────
app.get('/api/check-verification', (req, res) => {
  const { email } = req.query;
  if (!email) return res.status(400).json({ error: 'Email required' });

  let verified = false;
  for (const record of tokenStore.values()) {
    if (record.email === email && record.verified) {
      verified = true;
      break;
    }
  }
  res.json({ verified });
});

// ──────────────────────────────────────────────────────
// POST /api/resend-verification
// Body: { email }
// ──────────────────────────────────────────────────────
app.post('/api/resend-verification', async (req, res) => {
  const { email, firstName } = req.body;
  req.body = { email, firstName }; // reuse send handler
  return app._router.handle({ ...req, url: '/api/send-verification', path: '/api/send-verification', method: 'POST' }, res, () => {});
});

// Health check
app.get('/health', (_, res) => res.json({ status: 'ok', tokens: tokenStore.size }));

app.listen(PORT, () => {
  console.log(`\n🚀 Fleek email server running on http://localhost:${PORT}`);
  console.log(`📬 Resend API key: ${process.env.RESEND_API_KEY ? '✅ set' : '❌ MISSING – add to .env'}`);
  console.log(`🌐 App URL: ${APP_URL}\n`);
});

// ──────────────────────────────────────────────────────
// HTML EMAIL TEMPLATE
// ──────────────────────────────────────────────────────
function buildEmailHtml(firstName, verifyUrl) {
  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>Verify your Fleek Companion account</title>
</head>
<body style="margin:0;padding:0;background:#0a0a0f;font-family:'Inter',Helvetica,Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0a0a0f;padding:40px 16px;">
    <tr><td align="center">
      <table width="560" cellpadding="0" cellspacing="0" style="background:#1e1e28;border-radius:16px;overflow:hidden;border:1px solid rgba(255,255,255,0.08);max-width:100%;">

        <!-- Header -->
        <tr>
          <td style="background:linear-gradient(135deg,#7c3aed,#0891b2);padding:32px 40px;text-align:center;">
            <div style="font-size:28px;margin-bottom:6px;">⚡</div>
            <div style="color:#fff;font-size:22px;font-weight:800;letter-spacing:-0.5px;">fleek <span style="opacity:0.8;font-weight:400;">companion</span></div>
            <p style="color:rgba(255,255,255,0.75);margin:6px 0 0;font-size:13px;">Seller onboarding platform</p>
          </td>
        </tr>

        <!-- Body -->
        <tr>
          <td style="padding:36px 40px;">
            <p style="color:#a0a0b8;font-size:15px;margin:0 0 8px;">Hi <strong style="color:#f0f0f8;">${firstName}</strong>,</p>
            <h1 style="color:#f0f0f8;font-size:22px;font-weight:800;margin:0 0 16px;line-height:1.3;">Verify your email to unlock data import</h1>
            <p style="color:#a0a0b8;font-size:14px;line-height:1.7;margin:0 0 28px;">
              You're one step away from connecting your stores and importing your order history to Fleek.
              Click the button below to verify your email address and grant import authority.
            </p>

            <!-- CTA Button -->
            <table cellpadding="0" cellspacing="0" width="100%">
              <tr>
                <td align="center" style="padding-bottom:28px;">
                  <a href="${verifyUrl}"
                     style="display:inline-block;background:linear-gradient(135deg,#a855f7,#22d3ee);color:#fff;font-size:16px;font-weight:700;text-decoration:none;padding:16px 36px;border-radius:50px;letter-spacing:0.02em;box-shadow:0 4px 20px rgba(168,85,247,0.4);">
                    ✉️ &nbsp;Verify my email
                  </a>
                </td>
              </tr>
            </table>

            <!-- Info box -->
            <table cellpadding="0" cellspacing="0" width="100%"
                   style="background:#111118;border-radius:10px;border:1px solid rgba(255,255,255,0.06);margin-bottom:24px;">
              <tr><td style="padding:18px 22px;">
                <p style="color:#5a5a7a;font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:0.08em;margin:0 0 10px;">What happens next</p>
                <div style="display:flex;flex-direction:column;gap:8px;">
                  <p style="margin:0;color:#a0a0b8;font-size:13px;">📦 &nbsp;Connect your eBay, Shopify or Vinted stores</p>
                  <p style="margin:4px 0 0;color:#a0a0b8;font-size:13px;">📊 &nbsp;Your order history is securely imported</p>
                  <p style="margin:4px 0 0;color:#a0a0b8;font-size:13px;">🎙️ &nbsp;Enrich your profile with images &amp; voice notes</p>
                </div>
              </td></tr>
            </table>

            <p style="color:#5a5a7a;font-size:12px;line-height:1.6;margin:0;">
              Or copy this link into your browser:<br/>
              <span style="color:#7c3aed;word-break:break-all;">${verifyUrl}</span>
            </p>
          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td style="padding:20px 40px 32px;border-top:1px solid rgba(255,255,255,0.06);">
            <p style="color:#5a5a7a;font-size:12px;margin:0;text-align:center;line-height:1.6;">
              This link expires in <strong>24 hours</strong>. If you didn't create a Fleek Companion account, you can safely ignore this email.<br/>
              © 2025 Fleek Companion · <a href="#" style="color:#7c3aed;text-decoration:none;">Unsubscribe</a>
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>`;
}
