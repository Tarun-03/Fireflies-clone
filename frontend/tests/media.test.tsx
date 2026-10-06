// @vitest-environment jsdom
import { act, renderHook, cleanup } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { usePlayer } from "@/features/notebook/use-player";
afterEach(() => {
  cleanup();
  vi.useRealTimers();
});
it("uses controlled media time, preserves pause while seeking, and applies speed", async () => {
  vi.useFakeTimers();
  const { result } = renderHook(() => usePlayer(10000, true, 1));
  const media = {
    currentTime: 0,
    ended: false,
    playbackRate: 1,
    play: vi.fn().mockResolvedValue(undefined),
    pause: vi.fn(),
  } as unknown as HTMLAudioElement;
  act(() => {
    result.current.audio.current = media;
    result.current.seek(4500);
  });
  expect(media.currentTime).toBe(4.5);
  expect(result.current.playing).toBe(false);
  expect(media.play).not.toHaveBeenCalled();
  await act(async () => {
    await result.current.toggle();
  });
  expect(media.play).toHaveBeenCalledOnce();
  expect(result.current.playing).toBe(true);
  act(() => {
    media.currentTime = 7;
    vi.advanceTimersByTime(32);
  });
  expect(result.current.time).toBe(7000);
  act(() => result.current.setSpeed(1.5));
  expect(media.playbackRate).toBe(1.5);
  act(() => result.current.pause());
  expect(media.pause).toHaveBeenCalledOnce();
  expect(result.current.playing).toBe(false);
  act(() => result.current.seek(20000));
  expect(media.currentTime).toBe(10);
});
