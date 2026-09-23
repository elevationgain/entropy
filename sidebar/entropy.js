// entropy (in-window sidebar): every coding agent in THIS cmux window.
// Custom sidebars cannot see other windows; the web HUD (bin/entropy) can.
// Attention first (needs_input), then working, idle, and a capped ended list.
// Tap a row to jump to that agent's terminal.
//   cmux right-sidebar set custom entropy    (right panel)
//   cmux sidebar open entropy                (as a pane tab)

const STATUS = {
  needs_input: { label: "NEEDS YOU", short: "input", color: "#FF9F0A", strong: true },
  working: { label: "WORKING", short: "working", color: "#0A84FF", strong: false },
  idle: { label: "IDLE", short: "idle", color: "#34C759", strong: false },
  ended: { label: "ENDED", short: "ended", color: "#8E8E93", strong: false },
};
const ORDER = ["needs_input", "working", "idle", "ended"];
const ENDED_CAP = 5;

const epoch = () => data.clock()?.epoch ?? 0;

function ago(secs) {
  const s = Math.max(0, Math.floor(secs));
  if (s < 60) return s + "s";
  const m = Math.floor(s / 60);
  if (m < 60) return m + "m";
  const h = Math.floor(m / 60);
  return h < 24 ? h + "h" : Math.floor(h / 24) + "d";
}

function base(path) {
  if (!path) return "";
  const parts = String(path).split("/").filter(Boolean);
  return parts[parts.length - 1] ?? "";
}

const allAgents = computed(() => {
  const out = [];
  for (const w of data.workspaces() ?? []) {
    for (const a of w.agents ?? []) out.push({ key: w.id + ":" + a.id, ws: w, a });
  }
  return out;
});

// Stable ordering within a section: longest-waiting / longest-running first.
const byStatus = (status) =>
  computed(() => {
    const items = allAgents().filter((e) => e.a.status === status);
    const t = (e) => e.a.sinceEpoch ?? e.a.lastActivityAt ?? 0;
    items.sort((x, y) => (status === "ended" ? t(y) - t(x) : t(x) - t(y)) || (x.key < y.key ? -1 : 1));
    return status === "ended" ? items.slice(0, ENDED_CAP) : items;
  });

const count = (status) => computed(() => allAgents().filter((e) => e.a.status === status).length);

function jump(e) {
  cmux("workspace.select", { workspace_id: e.ws.id });
  if (e.a.surfaceId) cmux("surface.focus", { surface_id: e.a.surfaceId });
}

function chip(status) {
  const meta = STATUS[status];
  const n = count(status);
  return HStack({ spacing: 4 }, [
    Circle({ size: 6 }).fill(meta.color),
    Text(() => String(n())).font(11).monospaced().weight("semibold"),
    Text(meta.short).font(10).color("secondary"),
  ])
    .paddingHorizontal(7).paddingVertical(3)
    .cornerRadius(6)
    .background(() => (meta.strong && n() > 0 ? "#FF9F0A26" : "#7f7f7f14"));
}

function row(e, meta) {
  const since = () => e().a.sinceEpoch ?? e().a.lastActivityAt;
  return HStack({ spacing: 8 }, [
    Circle({ size: 7 }).fill(meta.color),
    VStack({ spacing: 1 }, [
      Text(() => e().a.title || e().a.name || e().a.kind)
        .font(12).weight(meta.strong ? "semibold" : "regular")
        .lineLimit(1).truncation("tail"),
      Text(() => {
        const a = e().a;
        const parts = [e().ws.title];
        const repo = base(a.directory ?? e().ws.directory);
        if (repo && repo !== e().ws.title) parts.push(repo);
        if (e().ws.branch) parts.push(e().ws.branch + (e().ws.dirty ? "*" : ""));
        if (a.kind && a.kind !== "claude") parts.push(a.kind);
        const subs = (a.children ?? []).filter((c) => c.running).length;
        if (subs) parts.push(subs + " sub");
        return parts.join(" · ");
      })
        .font(10).color("tertiary").lineLimit(1).truncation("tail"),
    ]),
    Spacer({ minLength: 0 }),
    Text(() => (since() ? ago(epoch() - since()) : ""))
      .font(10).monospaced().color(meta.strong ? meta.color : "tertiary"),
  ])
    .paddingHorizontal(10).paddingVertical(6)
    .cornerRadius(8)
    .opacity(meta === STATUS.ended ? 0.6 : 1)
    .background(meta.strong ? "#FF9F0A1a" : null)
    .hoverBackground(meta.strong ? "#FF9F0A2e" : "#7f7f7f24")
    .frame({ maxWidth: "infinity" })
    .onTap(() => jump(e()));
}

function section(status) {
  const meta = STATUS[status];
  const items = byStatus(status);
  const total = count(status);
  return VStack({ spacing: 3 }, [
    HStack({ spacing: 6 }, [
      Text(meta.label).font(10).weight("semibold")
        .color(() => (total() && meta.strong ? meta.color : "tertiary")),
      Spacer(),
      Text(() => (total() > items().length ? items().length + " of " + total() : total() ? String(total()) : ""))
        .font(10).monospaced().color("tertiary"),
    ]).paddingHorizontal(10),
    ForEach({ items, key: (e) => e.key }, (e) => row(e, meta)),
    Text(() => (total() === 0 ? "—" : "")).font(10).color("tertiary").paddingHorizontal(10),
  ]);
}

sidebar(
  () =>
    VStack({ spacing: 10 }, [
      HStack({ spacing: 6 }, [
        Text("Entropy").font(14).weight("semibold"),
        Spacer(),
        Text(() => (data.workspaceCount() ?? 0) + " ws · " + (data.clock()?.time ?? ""))
          .font(10).monospaced().color("tertiary"),
      ]).paddingHorizontal(10),
      HStack({ spacing: 6 }, ORDER.map(chip)).paddingHorizontal(10),
      Divider(),
      ...ORDER.map(section),
      Spacer(),
    ]).paddingHorizontal(6).paddingVertical(8),
  { surface: "glass" }
);
