// Kerangka aplikasi: AppShell responsif + nav berikon & berkelompok + logout.
import { AppShell, Badge, Burger, Group, NavLink, ScrollArea, Text } from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import {
  IconChartBar,
  IconSearch,
  IconAdjustments,
  IconServer,
  IconSpeakerphone,
  IconMessageDots,
  IconBox,
  IconUsers,
  IconSettings,
  IconLogout,
  IconShieldCheck,
  type Icon,
} from "@tabler/icons-react";
import { NavLink as RouterLink, Outlet, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";

interface Item {
  label: string;
  to: string;
  icon: Icon;
  admin?: boolean;
}
interface Section {
  title: string;
  items: Item[];
}

const SECTIONS: Section[] = [
  {
    title: "Pemantauan",
    items: [
      { label: "Analitik", to: "/", icon: IconChartBar },
      { label: "Pencarian", to: "/search", icon: IconSearch },
    ],
  },
  {
    title: "Administrasi",
    items: [
      { label: "Config", to: "/config", icon: IconAdjustments, admin: true },
      { label: "Layanan", to: "/services", icon: IconServer, admin: true },
      { label: "Campaign", to: "/campaigns", icon: IconSpeakerphone, admin: true },
      { label: "Feedback", to: "/feedback", icon: IconMessageDots, admin: true },
      { label: "Models", to: "/models", icon: IconBox, admin: true },
      { label: "Users", to: "/users", icon: IconUsers, admin: true },
    ],
  },
  {
    title: "Akun",
    items: [{ label: "Pengaturan", to: "/settings", icon: IconSettings }],
  },
];

export function AppLayout() {
  const [opened, { toggle }] = useDisclosure();
  const { role, logout } = useAuth();
  const navigate = useNavigate();
  const loc = useLocation();

  const onLogout = () => {
    logout();
    navigate("/login");
  };

  const visible = (s: Section) => s.items.filter((i) => !i.admin || role === "admin");

  return (
    <AppShell
      header={{ height: 56 }}
      navbar={{ width: 240, breakpoint: "sm", collapsed: { mobile: !opened } }}
      padding="md"
    >
      <AppShell.Header>
        <Group h="100%" px="md" justify="space-between">
          <Group gap="xs">
            <Burger opened={opened} onClick={toggle} hiddenFrom="sm" size="sm" />
            <IconShieldCheck size={22} color="var(--mantine-color-indigo-6)" />
            <Text fw={700}>Aegis</Text>
            <Text c="dimmed" size="sm" visibleFrom="sm">
              Anti-Fraud Dashboard
            </Text>
          </Group>
          <Group gap="sm">
            <Badge variant="light" color={role === "admin" ? "indigo" : "gray"} data-testid="role">
              {role}
            </Badge>
            <NavLink
              label="Keluar"
              leftSection={<IconLogout size={16} />}
              onClick={onLogout}
              w="auto"
              styles={{ root: { borderRadius: "var(--mantine-radius-md)" } }}
            />
          </Group>
        </Group>
      </AppShell.Header>

      <AppShell.Navbar p="xs">
        <ScrollArea>
          {SECTIONS.map((s) => {
            const items = visible(s);
            if (items.length === 0) return null;
            return (
              <div key={s.title}>
                <Text size="xs" fw={600} c="dimmed" tt="uppercase" px="sm" mt="md" mb={4}>
                  {s.title}
                </Text>
                {items.map((i) => {
                  const Ico = i.icon;
                  return (
                    <NavLink
                      key={i.to}
                      component={RouterLink}
                      to={i.to}
                      label={i.label}
                      leftSection={<Ico size={18} stroke={1.8} />}
                      active={loc.pathname === i.to}
                      onClick={() => opened && toggle()}
                    />
                  );
                })}
              </div>
            );
          })}
        </ScrollArea>
      </AppShell.Navbar>

      <AppShell.Main>
        <Outlet />
      </AppShell.Main>
    </AppShell>
  );
}
