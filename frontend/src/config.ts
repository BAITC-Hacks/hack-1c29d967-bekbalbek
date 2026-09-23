export type WorkspaceKind = "table" | "timeline" | "document";

export interface ChangeRow {
  id: string;
  label: string;        // e.g. "Order #4821"
  field: string;        // e.g. "Assigned worker"
  from: string;
  to: string;
  checks: { name: string; status: "pass" | "warn" | "fail" }[];
  why: string;          // plain-language reason
  evidence: { source: string; ref: string; snippet: string };
}

export interface SampleCase {
  id: string;
  title: string;
  severity: "critical" | "high" | "medium" | "low";
  owner: string;
  status: "new" | "analyzing" | "proposed" | "applied" | "verified";
  summary: string;
  workspace: WorkspaceKind;
  rows: { id: string; cells: string[] }[];
  columns: string[];
  changes: ChangeRow[];
  events: { key: string; label: string; detail: string; ms: number }[];
}

export const brand = {
  name: "Protokol",
  tagline: "Из разговора — в поручения.",
  sub: "Запись совещания на русском, казахском или смешанной речи: стенограмма, говорящие, решения и поручения с ответственными и сроками. Обработка локальными моделями.",
  ctaPrimary: "Открыть рабочее пространство", ctaSecondary: "Как это работает",
  announcement: "HackAlem AI · Трек 08 · Протоколы совещаний",
  nav: [{ label: "Возможности", href: "#tour" }, { label: "Процесс", href: "#how" }, { label: "Цитаты", href: "#signature" }, { label: "Совещания", href: "#/app" }],
  logos: [] as string[],
  stats: [{ value: "RU · KK", label: "русская, казахская и смешанная речь" }, { value: "Локально", label: "модели в контуре вашей команды" }, { value: "PDF · DOCX", label: "экспорт подтверждённого протокола" }],
};
export const landingCopy = {
  mockApply: "Подтвердить протокол", mockWhy: "Посмотреть цитату",
  tourHeading: "От записи до готового протокола.",
  tourResult: { title: "Совещание — пример протокола", body: "Краткое саммари, принятые решения и поручения. Каждый исполнитель и срок доступны для проверки по исходной реплике.", evidenceLabel: "Источник:", evidence: "Стенограмма · 00:07 · реплика №2" },
  signature: {
    heading: "У каждого поручения есть источник.",
    lead: "Откройте поручение и прочитайте реплику, на основании которой оно появилось. Уточните имена говорящих, проверьте сроки и подтвердите результат перед экспортом.",
    steps: ["Загрузка записи и дата совещания", "Распознавание русской и казахской речи", "Разделение реплик по говорящим", "Поручения с исполнителями, сроками и цитатами", "Подтверждение и экспорт в PDF / DOCX"],
    phases: { proposed: "Подтвердить протокол", applying: "Сохраняем…", applied: "Сохранено — проверяем", verified: "Протокол подтверждён" },
  },
  howHeading: "Четыре шага до результата.", ctaHeading: "Начните с вашей записи.", footer: "HackAlem AI · Локальная обработка совещаний",
};
export const heroScenes = [
  { kind: "activity" as const, title: "Совещание по развитию промышленности", lines: [
    { label: "Читаем данные совещания", detail: "get_meeting" },
    { label: "Изучаем реплики и говорящих", detail: "read_transcript" },
    { label: "Определяем сроки поручений", detail: "resolve_deadline" },
    { label: "Проект протокола готов к проверке", detail: "" },
  ] },
  { kind: "proposal" as const, title: "Пример поручений", rows: [
    { label: "Стратегия закупок", field: "Гульмира", from: "—", to: "15 октября" },
    { label: "График поставок", field: "Айнур", from: "—", to: "26 сентября" },
    { label: "Финансовое решение", field: "Тимур", from: "—", to: "30 сентября" },
  ] },
  { kind: "verified" as const, title: "Пример подтверждённого протокола", lines: ["Решения и поручения сохранены", "PDF и DOCX доступны для скачивания", "Статусы поручений — на одной странице"] },
];
export const tourTabs = [
  { id: "queue", label: "Загрузите запись", heading: "Все совещания под рукой.", body: "Добавьте аудио или видео, укажите название и фактическую дату встречи. Выберите запись, чтобы начать обработку.", mock: "table" as WorkspaceKind },
  { id: "analyze", label: "Наблюдайте за анализом", heading: "Видно, что делает агент.", body: "После распознавания агент читает стенограмму, ищет поручения и проверяет сроки. Его действия появляются в журнале по событиям сервера.", mock: "timeline" as WorkspaceKind },
  { id: "propose", label: "Проверьте поручения", heading: "От задачи — к исходной реплике.", body: "Исполнитель, срок, срочность и цитата в одном месте. Если дата не названа, это видно в результате.", mock: "table" as WorkspaceKind },
  { id: "verify", label: "Подтвердите и скачайте", heading: "Протокол готов к работе.", body: "Подтвердите проверенный результат, скачайте PDF или DOCX. Отмечайте выполнение поручений в локальном реестре.", mock: "document" as WorkspaceKind },
];
export const howItWorks = [
  { title: "Загрузите", body: "Добавьте запись и укажите дату совещания для расчёта относительных сроков." },
  { title: "Распознайте", body: "Локальные модели преобразуют речь в текст и разделяют реплики по говорящим." },
  { title: "Проверьте", body: "Сверьте поручения, исполнителей и сроки с цитатами из стенограммы." },
  { title: "Подтвердите", body: "Сохраните протокол, экспортируйте документ и отмечайте исполнение." },
];
export const sampleCases: SampleCase[] = [
  { id: "m-sample-1", title: "Развитие химической промышленности и ТБ", severity: "high", owner: "Секретарь", status: "proposed",
    summary: "Пример отображения поручений совещания.", workspace: "table", columns: ["Поручение", "Ответственный", "Срок"],
    rows: [{ id: "1", cells: ["Стратегия закупа сырья", "Гульмира Сериковна", "15 октября"] }, { id: "2", cells: ["График поставок", "Айнур Каировна", "26 сентября"] }, { id: "3", cells: ["Финансовое решение", "Тимур Болатович", "30 сентября"] }],
    changes: [{ id: "ch-1", label: "1", field: "Поручение", from: "Реплика совещания", to: "Разработать стратегию закупа сырья",
      checks: [{ name: "Есть источник", status: "pass" }, { name: "Назван исполнитель", status: "pass" }], why: "В реплике названы действие, ответственный и срок.",
      evidence: { source: "Пример цитаты", ref: "Стенограмма", snippet: "Разработать единую стратегию закупа сырья — ответственный Гульмира Сериковна, срок до 15 октября." } }],
    events: [{ key: "get_meeting", label: "Чтение совещания", detail: "дата и участники", ms: 900 }, { key: "read_transcript", label: "Чтение стенограммы", detail: "реплики с таймкодами", ms: 1100 }, { key: "resolve_deadline", label: "Проверка сроков", detail: "относительно даты встречи", ms: 800 }],
  },
  { id: "m-sample-2", title: "Оперативное совещание по отчётам департаментов", severity: "medium", owner: "Секретарь", status: "new",
    summary: "Пример задач по поставщикам, подрядчикам и обучению.", workspace: "table", columns: ["Поручение", "Ответственный", "Срок"],
    rows: [{ id: "4", cells: ["Подготовить претензию поставщику", "Ерлан", "До конца недели"] }], changes: [], events: [],
  },
];
