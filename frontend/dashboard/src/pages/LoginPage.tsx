import { Button, Card, Center, PasswordInput, Stack, Text, TextInput, ThemeIcon, Title } from "@mantine/core";
import { IconShieldCheck } from "@tabler/icons-react";
import { useForm } from "@mantine/form";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const form = useForm({ initialValues: { username: "", password: "" } });

  const submit = form.onSubmit(async (v) => {
    setError(null);
    setLoading(true);
    try {
      await login(v.username, v.password);
      navigate("/");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Gagal masuk.");
    } finally {
      setLoading(false);
    }
  });

  return (
    <Center h="100vh" p="md">
      <Card withBorder padding="xl" radius="lg" w={380} shadow="md">
        <Stack align="center" gap={4} mb="lg">
          <ThemeIcon variant="light" color="indigo" size={52} radius="md">
            <IconShieldCheck size={30} stroke={1.7} />
          </ThemeIcon>
          <Title order={3}>Masuk Aegis</Title>
          <Text size="sm" c="dimmed" ta="center">
            Dashboard anti-fraud — masuk untuk melanjutkan.
          </Text>
        </Stack>
        <form onSubmit={submit}>
          <Stack>
            <TextInput label="Username" {...form.getInputProps("username")} />
            <PasswordInput label="Password" {...form.getInputProps("password")} />
            {error && (
              <Text c="red" size="sm" role="alert">
                {error}
              </Text>
            )}
            <Button type="submit" loading={loading}>
              Masuk
            </Button>
          </Stack>
        </form>
      </Card>
    </Center>
  );
}
