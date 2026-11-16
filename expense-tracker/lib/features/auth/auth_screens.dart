import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:material_ui/material_ui.dart';

import '../../core/theme/app_theme.dart';
import '../../core/utils/extensions.dart';
import '../../services/auth_service.dart';
import 'auth_providers.dart';

class SplashScreen extends StatelessWidget {
  const SplashScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const _Logo(size: 72),
            const SizedBox(height: 20),
            Text('Expense & Budget Manager', style: context.text.titleMedium),
            const SizedBox(height: 24),
            const SizedBox(width: 28, height: 28, child: CircularProgressIndicator(strokeWidth: 2.5)),
          ],
        ).animate().fadeIn(duration: 400.ms),
      ),
    );
  }
}

class _Logo extends StatelessWidget {
  const _Logo({this.size = 64});
  final double size;

  @override
  Widget build(BuildContext context) {
    final scheme = context.colors;
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [scheme.primary, scheme.tertiary],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(size * 0.28),
        boxShadow: [
          BoxShadow(color: scheme.primary.withValues(alpha: 0.35), blurRadius: 24, offset: const Offset(0, 10)),
        ],
      ),
      child: Icon(Icons.account_balance_wallet_rounded, color: Colors.white, size: size * 0.52),
    );
  }
}

/// Shared scaffold for the auth screens: logo, title, form, footer.
class _AuthScaffold extends StatelessWidget {
  const _AuthScaffold({
    required this.title,
    required this.subtitle,
    required this.children,
    this.footer,
  });

  final String title;
  final String subtitle;
  final List<Widget> children;
  final Widget? footer;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 440),
            child: ListView(
              padding: const EdgeInsets.fromLTRB(24, 32, 24, 24),
              children: [
                const Align(alignment: Alignment.centerLeft, child: _Logo(size: 56)),
                const SizedBox(height: 24),
                Text(title, style: context.text.headlineMedium),
                const SizedBox(height: 6),
                Text(subtitle, style: context.text.bodyLarge?.copyWith(color: context.colors.onSurfaceVariant)),
                const SizedBox(height: 28),
                ...children,
                if (footer != null) ...[const SizedBox(height: 24), footer!],
              ].animate(interval: 40.ms).fadeIn(duration: 300.ms).slideY(begin: 0.05, end: 0),
            ),
          ),
        ),
      ),
    );
  }
}

class SignInScreen extends ConsumerStatefulWidget {
  const SignInScreen({super.key});

  @override
  ConsumerState<SignInScreen> createState() => _SignInScreenState();
}

class _SignInScreenState extends ConsumerState<SignInScreen> {
  final _form = GlobalKey<FormState>();
  final _email = TextEditingController();
  final _password = TextEditingController();
  bool _busy = false;
  bool _obscure = true;

  @override
  void dispose() {
    _email.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _run(Future<void> Function() action) async {
    setState(() => _busy = true);
    try {
      await action();
    } on AuthFailure catch (e) {
      if (mounted) context.showSnack(e.message, error: true);
    } catch (e) {
      if (mounted) context.showSnack('Something went wrong: $e', error: true);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final auth = ref.read(authServiceProvider);
    return _AuthScaffold(
      title: 'Welcome back',
      subtitle: 'Sign in to keep your budget on track.',
      footer: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text("Don't have an account?", style: context.text.bodyMedium),
          TextButton(onPressed: () => context.go('/sign-up'), child: const Text('Sign up')),
        ],
      ),
      children: [
        Form(
          key: _form,
          child: Column(
            children: [
              TextFormField(
                controller: _email,
                keyboardType: TextInputType.emailAddress,
                autofillHints: const [AutofillHints.email],
                textInputAction: TextInputAction.next,
                decoration: const InputDecoration(labelText: 'Email', prefixIcon: Icon(Icons.mail_outline_rounded)),
                validator: (v) => (v == null || !v.contains('@')) ? 'Enter a valid email' : null,
              ),
              const SizedBox(height: 14),
              TextFormField(
                controller: _password,
                obscureText: _obscure,
                autofillHints: const [AutofillHints.password],
                textInputAction: TextInputAction.done,
                onFieldSubmitted: (_) => _signIn(auth),
                decoration: InputDecoration(
                  labelText: 'Password',
                  prefixIcon: const Icon(Icons.lock_outline_rounded),
                  suffixIcon: IconButton(
                    icon: Icon(_obscure ? Icons.visibility_outlined : Icons.visibility_off_outlined),
                    onPressed: () => setState(() => _obscure = !_obscure),
                  ),
                ),
                validator: (v) => (v == null || v.length < 6) ? 'At least 6 characters' : null,
              ),
            ],
          ),
        ),
        Align(
          alignment: Alignment.centerRight,
          child: TextButton(
            onPressed: () => context.push('/forgot-password'),
            child: const Text('Forgot password?'),
          ),
        ),
        const SizedBox(height: 8),
        FilledButton(
          onPressed: _busy ? null : () => _signIn(auth),
          child: _busy
              ? const SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2.5, color: Colors.white))
              : const Text('Sign in'),
        ),
        const SizedBox(height: 20),
        Row(
          children: [
            const Expanded(child: Divider()),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12),
              child: Text('or continue with', style: context.text.bodySmall?.copyWith(color: context.colors.onSurfaceVariant)),
            ),
            const Expanded(child: Divider()),
          ],
        ),
        const SizedBox(height: 20),
        OutlinedButton.icon(
          onPressed: _busy ? null : () => _run(auth.signInWithGoogle),
          icon: const _GoogleMark(),
          label: const Text('Google'),
        ),
        const SizedBox(height: 12),
        OutlinedButton.icon(
          onPressed: _busy ? null : () => _run(auth.signInWithApple),
          icon: const Icon(Icons.apple_rounded, size: 24),
          label: const Text('Apple'),
        ),
      ],
    );
  }

  void _signIn(AuthService auth) {
    if (!_form.currentState!.validate()) return;
    _run(() => auth.signInWithEmail(_email.text, _password.text));
  }
}

class _GoogleMark extends StatelessWidget {
  const _GoogleMark();

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 22,
      height: 22,
      child: CustomPaint(painter: _GooglePainter()),
    );
  }
}

class _GooglePainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final rect = Rect.fromLTWH(2, 2, size.width - 4, size.height - 4);
    final stroke = size.width * 0.2;
    final paint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = stroke
      ..strokeCap = StrokeCap.butt;
    const colors = [Color(0xFF4285F4), Color(0xFF34A853), Color(0xFFFBBC05), Color(0xFFEA4335)];
    const sweeps = [1.1, 1.6, 1.0, 1.9];
    var start = -0.35;
    for (var i = 0; i < 4; i++) {
      paint.color = colors[i];
      canvas.drawArc(rect, start, sweeps[i], false, paint);
      start += sweeps[i];
    }
    paint
      ..style = PaintingStyle.fill
      ..color = const Color(0xFF4285F4);
    canvas.drawRect(Rect.fromLTWH(size.width / 2, size.height / 2 - stroke / 2, size.width / 2 - 2, stroke), paint);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

class SignUpScreen extends ConsumerStatefulWidget {
  const SignUpScreen({super.key});

  @override
  ConsumerState<SignUpScreen> createState() => _SignUpScreenState();
}

class _SignUpScreenState extends ConsumerState<SignUpScreen> {
  final _form = GlobalKey<FormState>();
  final _name = TextEditingController();
  final _email = TextEditingController();
  final _password = TextEditingController();
  bool _busy = false;

  @override
  void dispose() {
    _name.dispose();
    _email.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_form.currentState!.validate()) return;
    setState(() => _busy = true);
    try {
      await ref.read(authServiceProvider).signUpWithEmail(_name.text, _email.text, _password.text);
    } on AuthFailure catch (e) {
      if (mounted) context.showSnack(e.message, error: true);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return _AuthScaffold(
      title: 'Create your account',
      subtitle: 'Track spending together and reach your goals faster.',
      footer: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text('Already have an account?', style: context.text.bodyMedium),
          TextButton(onPressed: () => context.go('/sign-in'), child: const Text('Sign in')),
        ],
      ),
      children: [
        Form(
          key: _form,
          child: Column(
            children: [
              TextFormField(
                controller: _name,
                textCapitalization: TextCapitalization.words,
                autofillHints: const [AutofillHints.name],
                textInputAction: TextInputAction.next,
                decoration: const InputDecoration(labelText: 'Your name', prefixIcon: Icon(Icons.person_outline_rounded)),
                validator: (v) => (v == null || v.trim().length < 2) ? 'Enter your name' : null,
              ),
              const SizedBox(height: 14),
              TextFormField(
                controller: _email,
                keyboardType: TextInputType.emailAddress,
                autofillHints: const [AutofillHints.email],
                textInputAction: TextInputAction.next,
                decoration: const InputDecoration(labelText: 'Email', prefixIcon: Icon(Icons.mail_outline_rounded)),
                validator: (v) => (v == null || !v.contains('@')) ? 'Enter a valid email' : null,
              ),
              const SizedBox(height: 14),
              TextFormField(
                controller: _password,
                obscureText: true,
                autofillHints: const [AutofillHints.newPassword],
                textInputAction: TextInputAction.done,
                onFieldSubmitted: (_) => _submit(),
                decoration: const InputDecoration(labelText: 'Password', prefixIcon: Icon(Icons.lock_outline_rounded)),
                validator: (v) => (v == null || v.length < 6) ? 'At least 6 characters' : null,
              ),
            ],
          ),
        ),
        const SizedBox(height: 24),
        FilledButton(
          onPressed: _busy ? null : _submit,
          child: _busy
              ? const SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2.5, color: Colors.white))
              : const Text('Create account'),
        ),
        const SizedBox(height: 12),
        Text(
          'By continuing you agree that your data is stored securely in your own Firebase project.',
          textAlign: TextAlign.center,
          style: context.text.bodySmall?.copyWith(color: context.colors.onSurfaceVariant),
        ),
      ],
    );
  }
}

class ForgotPasswordScreen extends ConsumerStatefulWidget {
  const ForgotPasswordScreen({super.key});

  @override
  ConsumerState<ForgotPasswordScreen> createState() => _ForgotPasswordScreenState();
}

class _ForgotPasswordScreenState extends ConsumerState<ForgotPasswordScreen> {
  final _email = TextEditingController();
  bool _busy = false;
  bool _sent = false;

  @override
  void dispose() {
    _email.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_email.text.contains('@')) {
      context.showSnack('Enter a valid email', error: true);
      return;
    }
    setState(() => _busy = true);
    try {
      await ref.read(authServiceProvider).sendPasswordReset(_email.text);
      setState(() => _sent = true);
    } on AuthFailure catch (e) {
      if (mounted) context.showSnack(e.message, error: true);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return _AuthScaffold(
      title: 'Reset password',
      subtitle: "We'll email you a link to choose a new password.",
      footer: TextButton(onPressed: () => context.pop(), child: const Text('Back to sign in')),
      children: [
        if (_sent)
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: AppTheme.income.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(14),
            ),
            child: Row(
              children: [
                const Icon(Icons.check_circle_rounded, color: AppTheme.income),
                const SizedBox(width: 12),
                Expanded(child: Text('Check your inbox for the reset link.', style: context.text.bodyMedium)),
              ],
            ),
          )
        else ...[
          TextField(
            controller: _email,
            keyboardType: TextInputType.emailAddress,
            decoration: const InputDecoration(labelText: 'Email', prefixIcon: Icon(Icons.mail_outline_rounded)),
            onSubmitted: (_) => _submit(),
          ),
          const SizedBox(height: 20),
          FilledButton(onPressed: _busy ? null : _submit, child: const Text('Send reset link')),
        ],
      ],
    );
  }
}
