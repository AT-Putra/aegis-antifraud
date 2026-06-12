// Kerangka aplikasi: AppShell responsif + nav role-gated + logout.
import { AppShell, Burger, Group, NavLink, ScrollArea, Text, Button } from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { NavLink as RouterLink, Outlet, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";

interface Item {
  label: string;
  to: string;
  admin?: boolean;
}
const ITEMS: Item[] = [
  { label: "Analitik", to: "/" },
  { label: "Pencarian", to: "/search" },
  { label: "Config", to: "/config", admin: true },
  { label: "Layanan", to: "/services", admin: true },
  { label: "Campaign", to: "/campaigns", admin: true },
  { label: "Feedback", to: "/feedback" },
  { label: "Users", to: "/users", admin: true },
  { label: "Pengaturan", to: "/settings" },
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

  return (
    <AppShell
      header={{ height: 56 }}
      navbar={{ width: 220, breakpoint: "sm", collapsed: { mobile: !opened } }}
      padding="md"
    >
      <AppShell.Header>
        <Group h="100%" px="md" justify="space-between">
          <Group>
            <Burger opened={opened} onClick={toggle} hiddenFrom="sm" size="sm" />
            <Text fw={700}>Aegis</Text>
            <Text c="dimmed" size="sm" visibleFrom="sm">
              Anti-Fraud Dashboard
            </Text>
          </Group>
          <Group>
            <Text size="sm" c="dimmed" data-testid="role">
              {role}
            </Text>
            <Button size="xs" variant="light" onClick={onLogout}>
              Keluar
            </Button>
          </Group>
        </Group>
      </AppShell.Header>

      <AppShell.Navbar p="xs">
        <ScrollArea>
          {ITEMS.filter((i) => !i.admin || role === "admin").map((i) => (
            <NavLink
              key={i.to}
              component={RouterLink}
              to={i.to}
              label={i.label}
              active={loc.pathname === i.to}
              onClick={() => opened && toggle()}
            />
          ))}
        </ScrollArea>
      </AppShell.Navbar>

      <AppShell.Main>
        <Outlet />
      </AppShell.Main>
    </AppShell>
  );
}
