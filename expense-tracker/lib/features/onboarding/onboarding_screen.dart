import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:material_ui/material_ui.dart';

import '../../core/constants/app_icons.dart';
import '../../core/constants/currencies.dart';
import '../../core/utils/extensions.dart';
import '../../core/widgets/widgets.dart';
import '../auth/auth_providers.dart';
import '../household/household_providers.dart';

/// First-run flow: make sure a profile exists, then create or join a household.
class OnboardingScreen extends ConsumerStatefulWidget {
  const OnboardingScreen({super.key});

  @override
  ConsumerState<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends ConsumerState<OnboardingScreen> {
  final _name = TextEditingController(text: 'My Household');
  String _currency = kDefaultCurrency;
  bool _busy = false;
  int _page = 0;
  final _pager = PageController();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _ensureProfile());
  }

  Future<void> _ensureProfile() async {
    final user = ref.read(authStateProvider).value;
    if (user == null) return;
    try {
      await ref.read(userRepositoryProvider).ensureProfile(user);
    } catch (e) {
      if (mounted) context.showSnack('Could not load your profile: $e', error: true);
    }
  }

  @override
  void dispose() {
    _name.dispose();
    _pager.dispose();
    super.dispose();
  }

  Future<void> _create() async {
    final user = ref.read(authStateProvider).value;
    if (user == null) return;
    setState(() => _busy = true);
    try {
      final repo = ref.read(userRepositoryProvider);
      final profile = await repo.ensureProfile(user);
      await repo.createHousehold(profile: profile, name: _name.text, currency: _currency);
    } catch (e) {
      if (mounted) context.showSnack('Could not create household: $e', error: true);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final scheme = context.colors;
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 480),
            child: Column(
              children: [
                Expanded(
                  child: PageView(
                    controller: _pager,
                    onPageChanged: (i) => setState(() => _page = i),
                    children: [
                      const _IntroPage(
                        icon: Icons.receipt_long_rounded,
                        title: 'Every rupee, accounted for',
                        body: 'Log expenses in seconds with smart categories, receipts, tags and recurring bills.',
                      ),
                      const _IntroPage(
                        icon: Icons.family_restroom_rounded,
                        title: 'Budget as a family',
                        body: 'Invite your family with a code. Shared accounts and budgets update live on every phone.',
                      ),
                      const _IntroPage(
                        icon: Icons.insights_rounded,
                        title: 'Understand your money',
                        body: 'Trends, category breakdowns, forecasts and one-tap PDF or Excel reports.',
                      ),
                      _SetupPage(
                        nameController: _name,
                        currency: _currency,
                        onCurrency: (c) => setState(() => _currency = c),
                      ),
                    ],
                  ),
                ),
                Padding(
                  padding: const EdgeInsets.fromLTRB(24, 0, 24, 24),
                  child: Column(
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: List.generate(
                          4,
                          (i) => AnimatedContainer(
                            duration: const Duration(milliseconds: 200),
                            margin: const EdgeInsets.symmetric(horizontal: 3),
                            width: i == _page ? 22 : 8,
                            height: 8,
                            decoration: BoxDecoration(
                              color: i == _page ? scheme.primary : scheme.outlineVariant,
                              borderRadius: BorderRadius.circular(4),
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(height: 20),
                      if (_page < 3)
                        FilledButton(
                          onPressed: () => _pager.nextPage(
                            duration: const Duration(milliseconds: 300),
                            curve: Curves.easeOutCubic,
                          ),
                          child: Text(_page == 2 ? 'Set up my household' : 'Next'),
                        )
                      else
                        FilledButton(
                          onPressed: _busy ? null : _create,
                          child: _busy
                              ? const SizedBox(
                                  width: 22,
                                  height: 22,
                                  child: CircularProgressIndicator(strokeWidth: 2.5, color: Colors.white),
                                )
                              : const Text('Create household'),
                        ),
                      const SizedBox(height: 8),
                      TextButton(
                        onPressed: () => context.push('/onboarding/join'),
                        child: const Text('Have an invite code? Join a family'),
                      ),
                      TextButton(
                        onPressed: () => ref.read(authServiceProvider).signOut(),
                        child: Text('Sign out', style: TextStyle(color: scheme.onSurfaceVariant)),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _IntroPage extends StatelessWidget {
  const _IntroPage({required this.icon, required this.title, required this.body});
  final IconData icon;
  final String title;
  final String body;

  @override
  Widget build(BuildContext context) {
    final scheme = context.colors;
    return Padding(
      padding: const EdgeInsets.all(32),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Container(
            width: 140,
            height: 140,
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [scheme.primaryContainer, scheme.tertiaryContainer],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(44),
            ),
            child: Icon(icon, size: 64, color: scheme.primary),
          ).animate().scale(duration: 500.ms, curve: Curves.easeOutBack),
          const SizedBox(height: 36),
          Text(title, style: context.text.headlineSmall, textAlign: TextAlign.center),
          const SizedBox(height: 12),
          Text(
            body,
            style: context.text.bodyLarge?.copyWith(color: scheme.onSurfaceVariant),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }
}

class _SetupPage extends StatelessWidget {
  const _SetupPage({
    required this.nameController,
    required this.currency,
    required this.onCurrency,
  });

  final TextEditingController nameController;
  final String currency;
  final ValueChanged<String> onCurrency;

  @override
  Widget build(BuildContext context) {
    final info = currencyInfo(currency);
    return ListView(
      padding: const EdgeInsets.all(28),
      children: [
        Text('Your household', style: context.text.headlineSmall),
        const SizedBox(height: 8),
        Text(
          'A household is where your accounts, budgets and transactions live. Invite family later from the Family tab.',
          style: context.text.bodyMedium?.copyWith(color: context.colors.onSurfaceVariant),
        ),
        const SizedBox(height: 28),
        TextField(
          controller: nameController,
          textCapitalization: TextCapitalization.words,
          decoration: const InputDecoration(labelText: 'Household name', prefixIcon: Icon(Icons.home_rounded)),
        ),
        const SizedBox(height: 14),
        AppCard(
          onTap: () async {
            final picked = await showCurrencyPicker(context, selected: currency);
            if (picked != null) onCurrency(picked);
          },
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          child: Row(
            children: [
              IconBadge(iconKey: 'currency_exchange', color: kPalette[9], size: 40),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Base currency', style: context.text.labelMedium?.copyWith(color: context.colors.onSurfaceVariant)),
                    Text('${info.code} · ${info.name}', style: context.text.titleSmall),
                  ],
                ),
              ),
              const Icon(Icons.chevron_right_rounded),
            ],
          ),
        ),
      ],
    );
  }
}

/// Enter an 8-character invite code to join an existing household.
class JoinHouseholdScreen extends ConsumerStatefulWidget {
  const JoinHouseholdScreen({super.key});

  @override
  ConsumerState<JoinHouseholdScreen> createState() => _JoinHouseholdScreenState();
}

class _JoinHouseholdScreenState extends ConsumerState<JoinHouseholdScreen> {
  final _code = TextEditingController();
  bool _busy = false;

  @override
  void dispose() {
    _code.dispose();
    super.dispose();
  }

  Future<void> _join() async {
    final user = ref.read(authStateProvider).value;
    if (user == null) return;
    if (_code.text.trim().length < 6) {
      context.showSnack('Enter the full invite code', error: true);
      return;
    }
    setState(() => _busy = true);
    try {
      final repo = ref.read(userRepositoryProvider);
      final profile = await repo.ensureProfile(user);
      final household = await repo.joinHousehold(
        profile: profile,
        code: _code.text,
        memberColor: kPalette[(profile.uid.hashCode.abs()) % kPalette.length],
      );
      if (!mounted) return;
      context.showSnack('Welcome to ${household.name}!');
      if (context.canPop()) context.pop();
    } on StateError catch (e) {
      if (mounted) context.showSnack(e.message, error: true);
    } catch (e) {
      if (mounted) context.showSnack('Could not join: $e', error: true);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final profile = ref.watch(userProfileProvider).value;
    final hasHousehold = profile?.activeHouseholdId != null;
    return Scaffold(
      appBar: AppBar(title: const Text('Join a family')),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 440),
          child: ListView(
            padding: const EdgeInsets.all(24),
            children: [
              const Icon(Icons.group_add_rounded, size: 56),
              const SizedBox(height: 16),
              Text(
                'Ask a family member for the invite code shown in their Family tab.',
                textAlign: TextAlign.center,
                style: context.text.bodyLarge?.copyWith(color: context.colors.onSurfaceVariant),
              ),
              const SizedBox(height: 28),
              TextField(
                controller: _code,
                textCapitalization: TextCapitalization.characters,
                autocorrect: false,
                textAlign: TextAlign.center,
                style: context.text.headlineSmall?.copyWith(letterSpacing: 6),
                decoration: const InputDecoration(hintText: 'ABCD2345'),
                onSubmitted: (_) => _join(),
              ),
              const SizedBox(height: 20),
              FilledButton(
                onPressed: _busy ? null : _join,
                child: _busy
                    ? const SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2.5, color: Colors.white))
                    : const Text('Join household'),
              ),
              if (hasHousehold) ...[
                const SizedBox(height: 12),
                Text(
                  'Joining switches your active household. You can switch back any time from the Family tab.',
                  textAlign: TextAlign.center,
                  style: context.text.bodySmall?.copyWith(color: context.colors.onSurfaceVariant),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
