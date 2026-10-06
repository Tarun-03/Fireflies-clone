"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Bell,
  CalendarDays,
  CheckSquare,
  ChevronDown,
  Hash,
  Menu,
  MoreHorizontal,
  Plug,
  Plus,
  Search,
  Settings,
  Upload,
  Users,
  Video,
} from "lucide-react";
import * as Dropdown from "@radix-ui/react-dropdown-menu";
import { Avatar } from "./avatar";
import { Dialog, ErrorNotice } from "./dialog";
import { useAction, useApi } from "./providers";
import { CreateDialog } from "@/features/library/create-dialog";
import { TagDialog } from "@/features/library/tag-dialog";
import type { Activity, Page, Profile, Tag } from "@/lib/types";
import { SearchDialog } from "@/features/search/search-dialog";
import { dateLabel } from "@/lib/time";

const navigation = [
  { href: "/", label: "Meetings", icon: CalendarDays },
  { href: "/uploads", label: "Uploads", icon: Upload },
  { href: "/tasks", label: "Action items", icon: CheckSquare },
];
export function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const profile = useApi<Profile>("me");
  const tags = useApi<Page<Tag>>("tags");
  const [create, setCreate] = useState(false);
  const [mobile, setMobile] = useState(false);
  const [search, setSearch] = useState(false);
  const [notifications, setNotifications] = useState(false);
  const [tag, setTag] = useState<Tag | "new" | null>(null);
  useEffect(() => {
    const shortcut = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setSearch((value) => !value);
      }
    };
    document.addEventListener("keydown", shortcut);
    return () => document.removeEventListener("keydown", shortcut);
  }, []);
  const sidebar = (
    <>
      <Link className="brand" href="/" aria-label="fireflies meetings">
        <svg width="29" height="30" viewBox="0 0 30 30" aria-hidden="true">
          <path
            d="M15 2C9 6 8 11 12 15C7 14 3 17 3 21C3 27 13 28 17 22C22 26 28 20 25 15C23 12 20 11 17 12C20 8 19 4 15 2Z"
            fill="currentColor"
          />
        </svg>
        fireflies
      </Link>
      <div className="workspace-name">
        <span className="workspace-square">A</span>
        <span>
          Acme workspace<small>Personal demo</small>
        </span>
        <ChevronDown size={15} />
      </div>
      <nav aria-label="Main navigation">
        {navigation.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            onClick={() => setMobile(false)}
            className={`nav-item ${pathname === href ? "selected" : ""}`}
          >
            <Icon size={18} />
            {label}
          </Link>
        ))}
      </nav>
      <div className="nav-label">WORKSPACE</div>
      <nav aria-label="Workspace tools">
        <Link href="/integrations" className="nav-item">
          <Plug size={18} />
          Integrations
        </Link>
        <Link href="/team" className="nav-item">
          <Users size={18} />
          Team
        </Link>
        <Link href="/live" className="nav-item">
          <Video size={18} />
          Meeting bot
        </Link>
      </nav>
      <div className="nav-label row-between">
        TAGS
        <button
          className="icon-button"
          aria-label="Create tag"
          onClick={() => setTag("new")}
        >
          <Plus size={15} />
        </button>
      </div>
      <nav aria-label="Tags">
        {tags.data?.items.map((item) => (
          <div key={item.id} className="tag-nav">
            <Link
              className="nav-item"
              href={`/?tag=${item.id}`}
              onClick={() => setMobile(false)}
            >
              <Hash size={16} className={`color-${item.color}`} />
              {item.name}
            </Link>
            <button
              className="icon-button"
              aria-label={`Edit ${item.name} tag`}
              onClick={() => setTag(item)}
            >
              <MoreHorizontal size={15} />
            </button>
          </div>
        ))}
      </nav>
      <div className="sidebar-footer">
        <Link href="/settings" className="nav-item">
          <Settings size={18} />
          Settings & about
        </Link>
        <div className="profile-row">
          <Avatar name={profile.data?.display_name ?? "Alex Morgan"} />
          <span>
            {profile.data?.display_name ?? "Alex Morgan"}
            <small>Private workspace</small>
          </span>
        </div>
      </div>
    </>
  );
  return (
    <div className="app-shell">
      <a href="#main" className="skip-link">
        Skip to content
      </a>
      <aside className="sidebar">{sidebar}</aside>
      <div className="main-shell">
        <header className="utility-bar">
          <button
            className="icon-button mobile-only"
            onClick={() => setMobile(true)}
            aria-label="Open navigation"
          >
            <Menu size={21} />
          </button>
          <button className="global-trigger" onClick={() => setSearch(true)}>
            <Search size={17} />
            <span>Search all meetings</span>
            <kbd>⌘ K</kbd>
          </button>
          <div className="utility-actions">
            <button
              className="icon-button"
              aria-label="Notifications"
              onClick={() => setNotifications(true)}
            >
              <Bell size={19} />
            </button>
            <Dropdown.Root>
              <Dropdown.Trigger
                className="icon-button"
                aria-label="Profile menu"
              >
                <Avatar
                  name={profile.data?.display_name ?? "Alex Morgan"}
                  small
                />
              </Dropdown.Trigger>
              <Dropdown.Portal>
                <Dropdown.Content className="dropdown" align="end">
                  <Dropdown.Item asChild>
                    <Link href="/settings">Settings & about</Link>
                  </Dropdown.Item>
                </Dropdown.Content>
              </Dropdown.Portal>
            </Dropdown.Root>
            <button
              className="primary create-button"
              aria-label="Create meeting"
              onClick={() => setCreate(true)}
            >
              <Plus size={17} />
              <span>Create meeting</span>
            </button>
          </div>
        </header>
        <main id="main" className="main-content">
          {children}
        </main>
      </div>
      <Dialog open={mobile} onOpenChange={setMobile} title="Your workspace">
        <div className="mobile-nav">{sidebar}</div>
      </Dialog>
      {create && <CreateDialog open onOpenChange={setCreate} />}
      {tag && <TagDialog tag={tag} onClose={() => setTag(null)} />}
      {search && <SearchDialog onClose={() => setSearch(false)} />}
      {notifications && (
        <Notifications onClose={() => setNotifications(false)} />
      )}
    </div>
  );
}
function Notifications({ onClose }: { onClose: () => void }) {
  const result = useApi<Page<Activity>>("activity");
  const action = useAction();
  return (
    <Dialog
      title="Notifications"
      description="Activity in your private workspace."
      open
      onOpenChange={onClose}
    >
      <ErrorNotice error={result.error ?? action.error} />
      <div className="notification-list">
        {result.isLoading ? (
          <p>Loading activity…</p>
        ) : !result.data?.items.length ? (
          <p>You’re all caught up. Your meeting activity will appear here.</p>
        ) : (
          result.data.items.map((event) => (
            <div key={event.id} className="notification">
              <span className={event.is_read ? "read-dot" : "unread-dot"} />
              <span>
                {event.text}
                <small>{dateLabel(event.created_at)}</small>
              </span>
              {!event.is_read && (
                <button
                  disabled={action.isPending}
                  onClick={() =>
                    action.mutate({
                      path: `activity/${event.id}`,
                      method: "PATCH",
                      version: event.version,
                      body: { is_read: true },
                    })
                  }
                >
                  Mark read
                </button>
              )}
            </div>
          ))
        )}
      </div>
    </Dialog>
  );
}
