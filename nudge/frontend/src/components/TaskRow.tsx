// One task in a list. Tap the circle (or swipe right) to close; swipe left to snooze to tomorrow;
// the ⋯ button opens every other action (also reachable by keyboard).
import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import type { ShortTask } from "../api";
import { dueText, plural, timeAgo } from "../format";
import { Icon } from "../icons";
import { useApp, useTaskActions } from "../store";
import { BasketDot } from "../ui";

const SWIPE = 90;

export function TaskRow({ task, showBasket = true, compact = false }: { task: ShortTask; showBasket?: boolean; compact?: boolean }) {
  const nav = useNavigate();
  const { setMenuFor } = useApp();
  const actions = useTaskActions();
  const [dx, setDx] = useState(0);
  const [gone, setGone] = useState(false);
  const start = useRef<{ x: number; y: number; id: number } | null>(null);
  const swiping = useRef(false);
  const closed = task.status === "done" || task.status === "dropped";
  const due = dueText(task);

  const onDown = (e: React.PointerEvent) => {
    if (closed || e.pointerType === "mouse") return;
    start.current = { x: e.clientX, y: e.clientY, id: e.pointerId };
    swiping.current = false;
  };
  const onMove = (e: React.PointerEvent) => {
    if (!start.current) return;
    const ddx = e.clientX - start.current.x;
    const ddy = e.clientY - start.current.y;
    if (!swiping.current && Math.abs(ddx) > 12 && Math.abs(ddx) > Math.abs(ddy) * 1.5) {
      swiping.current = true;
      (e.currentTarget as HTMLElement).setPointerCapture(start.current.id);
    }
    if (swiping.current) setDx(Math.max(-160, Math.min(160, ddx)));
  };
  const onUp = () => {
    if (!start.current) return;
    start.current = null;
    if (dx > SWIPE) {
      setGone(true);
      actions.complete(task);
    } else if (dx < -SWIPE) {
      setGone(true);
      actions.snooze(task, "tomorrow");
    }
    setDx(0);
    window.setTimeout(() => (swiping.current = false), 0);
  };

  const open = () => {
    if (!swiping.current) nav(`/task/${task.id}`);
  };

  if (gone) return null;
  return (
    <div className="trow-wrap">
      {dx !== 0 && (
        <div className={`trow-bg ${dx > 0 ? "done" : "snooze"}`} aria-hidden="true">
          {dx > 0 ? <span className="row"><Icon name="check" /> Done</span> : <span className="row">Tomorrow <Icon name="calendar" /></span>}
        </div>
      )}
      <div className={`trow ${dx ? "dragging" : ""} ${closed ? "closed" : ""}`} style={{ transform: dx ? `translateX(${dx}px)` : undefined }}
        onPointerDown={onDown} onPointerMove={onMove} onPointerUp={onUp} onPointerCancel={onUp}>
        <button className={`check ${closed ? "done" : ""} ${task.priority === "high" && !closed ? "high" : ""}`}
          aria-label={closed ? `Reopen ${task.title}` : `Mark done: ${task.title}`}
          onClick={(e) => { e.stopPropagation(); if (closed) actions.reopen(task); else { setGone(true); actions.complete(task); } }}>
          <Icon name="check" size={15} strokeWidth={3} />
        </button>
        <div className="tbody" onClick={open} role="link" tabIndex={0} onKeyDown={(e) => e.key === "Enter" && open()}>
          <div className="ttitle">
            {task.focus && !closed && <Icon name="star" size={14} style={{ color: "var(--c-amber)", marginRight: 6, verticalAlign: -1, fill: "currentColor" }} />}
            {task.title}
          </div>
          {!compact && (
            <div className="tmeta">
              {closed && <span><Icon name="done" size={13} />{task.status === "done" ? "Done" : "Dropped"}{task.closed_at ? ` ${timeAgo(task.closed_at)}` : ""}</span>}
              {!closed && due.text && <span className={due.tone === "over" ? "due-over" : due.tone === "today" ? "due-today" : ""}>
                <Icon name={due.tone === "over" ? "alert" : "calendar"} size={13} />{due.text}</span>}
              {task.status === "waiting" && <span><Icon name="hourglass" size={13} />Waiting on {task.person}{task.waiting_days != null ? ` · ${plural(task.waiting_days, "day")}` : ""}</span>}
              {task.status !== "waiting" && task.person && <span><Icon name="user" size={13} />{task.person}</span>}
              {showBasket && task.basket && <span><BasketDot basket={task.basket} />{task.basket.name}</span>}
              {task.repeat_label && <span><Icon name="repeat" size={13} />{task.repeat_label}</span>}
              {(task.checklist_total ?? 0) > 0 && <span><Icon name="list" size={13} />{task.checklist_done}/{task.checklist_total}</span>}
              {task.priority === "high" && !closed && <span className="badge critical">High</span>}
              {task.ai_fields.length > 0 && !closed && <span className="badge guess"><Icon name="sparkle" size={12} />Check details</span>}
            </div>
          )}
        </div>
        {!closed && (
          <button className="icon-btn" aria-label={`More actions for ${task.title}`} onClick={(e) => { e.stopPropagation(); setMenuFor(task); }}>
            <Icon name="more" />
          </button>
        )}
      </div>
    </div>
  );
}

export function TaskList({ tasks, showBasket = true, empty }: { tasks: ShortTask[]; showBasket?: boolean; empty?: React.ReactNode }) {
  if (!tasks.length) return <>{empty}</>;
  return (
    <div className="tlist">
      {tasks.map((t) => <TaskRow key={`${t.id}-${t.status}-${t.due_date}`} task={t} showBasket={showBasket} />)}
    </div>
  );
}
