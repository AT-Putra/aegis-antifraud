// Toggle tema manual: siklus terang → gelap → ikut-sistem (auto).
// Memakai useMantineColorScheme (in-stack Mantine) — preferensi UI klien, tanpa backend.
import { ActionIcon, Tooltip, useMantineColorScheme } from "@mantine/core";
import { IconDeviceDesktop, IconMoon, IconSun } from "@tabler/icons-react";

type Scheme = "light" | "dark" | "auto";
const NEXT: Record<Scheme, Scheme> = { light: "dark", dark: "auto", auto: "light" };
const LABEL: Record<Scheme, string> = {
  light: "Tema: terang",
  dark: "Tema: gelap",
  auto: "Tema: ikut sistem",
};

export function ThemeToggle() {
  const { colorScheme, setColorScheme } = useMantineColorScheme();
  const current = (colorScheme as Scheme) ?? "auto";

  const Icon =
    current === "light" ? IconSun : current === "dark" ? IconMoon : IconDeviceDesktop;

  return (
    <Tooltip label={LABEL[current]} withArrow>
      <ActionIcon
        variant="default"
        size="lg"
        radius="md"
        aria-label={LABEL[current]}
        onClick={() => setColorScheme(NEXT[current])}
      >
        <Icon size={18} stroke={1.8} />
      </ActionIcon>
    </Tooltip>
  );
}
