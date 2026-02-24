"use client"
import React, { useState, useMemo, useEffect, useCallback, useRef } from "react"
import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { calSans } from "@/font/font"
import {
  Search,
  Filter,
  CheckCircle,
  ChevronLeft,
  ChevronRight,
  Copy,
  FileText,
  Calendar,
  ExternalLink,
  Scale,
  Sparkles,
  BookOpenText,
  FileCheck2,
} from "lucide-react"
import { LoadingState } from "@/components/loading/loading"
import { EmptyState } from "@/components/loading/empty"
import Image from "next/image"

interface Laws {
  obligation_id: string;
  agency: string;
  citation: string;
  excerpt: string;
  title: string;
  instrument_type: string;
  jurisdiction: string;
  source_url: string;
  must_do: string;
  conditions: string | null;
  artifacts_required: string[];
  summary_bullets: string[];
  review_status: string;
  confidence: number | null;
}

const AGENCY_MAP = {
  "fincen": "FINCEN",
  "occ": "OCC",
  "fdic": "FDIC",
  "frb": "FRB",
  "cfpb": "CFPB",
  "ofac": "OFAC",
  "ffiec": "FFIEC",
  "ncua": "NCUA",
  "hud": "HUD",
  "congress": "CONGRESS",
  "nj_dobi": "NJ DOBI",
  "nj_attorney_general": "NJ AG",
  "nj_ag": "NJ AG"
}

const TOPIC_MAP = {
  sanctions: "Sanctions",
  aml_bsa: "AML/BSA",
  ctr: "CTR",
  sar: "SAR",
  money_transmitter: "Money Transmitter",
  beneficial_ownership: "Beneficial Ownership",
  recordkeeping: "Recordkeeping",
  risk_assessment: "Risk Assessment",
  privacy: "Privacy",
  licensing: "Licensing",
  cdd_kyc: "KYC/CIP"
};

const TOPIC_FILTER_MAP: Record<string, string[]> = {
  "AML/BSA": ["aml_bsa"],
  "SAR": ["aml_bsa"],
  "CTR": ["ctr"],
  "KYC/CIP": ["cdd_kyc", "beneficial_ownership"],
  "Money Transmitter": ["money_transmitter"],
  "Sanctions": ["sanctions"],
  "Compliance": ["licensing", "recordkeeping", "risk_assessment", "privacy"],
  "Beneficial Ownership": ["beneficial_ownership"],
  "Recordkeeping": ["recordkeeping"],
  "Risk Assessment": ["risk_assessment"],
  "Privacy": ["privacy"],
  "Licensing": ["licensing"],
};

const TOPIC_FILTER_MAP_NORMALIZED = Object.fromEntries(
  Object.entries(TOPIC_FILTER_MAP).map(([key, value]) => [key.toLowerCase(), value])
);

const FRUIT_OPTIONS = ["Keyword","Citation"] as const

const JURISDICTIONS = ["Federal", "New Jersey"]
const AGENCIES = [
  "FINCEN",
  "OCC",
  "FDIC",
  "FRB",
  "CFPB",
  "OFAC",
  "FFIEC",
  "NCUA",
  "HUD",
  "CONGRESS",
  "NJ DOBI",
  "NJ AG",
]
const DOCUMENT_TYPES = [
  "Regulation",
  "Statute",
  "Bulletin",
  "Advisory",
  "Manual",
  "Letter",
  "Circular",
]
const TOPICS = [
  "AML/BSA",
  "SAR",
  "CTR",
  "KYC/CIP",
  "Money Transmitter",
  "Sanctions",
  "Beneficial Ownership",
  "Recordkeeping",
  "Risk Assessment",
  "Privacy",
  "Licensing",
  "Compliance",
]

const humanizeTopic = (value: string) =>
  value.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

const normalizeTopicLabel = (raw: string): string => {
  if (!raw) return "";
  const key = raw.toLowerCase() as keyof typeof TOPIC_MAP;
  return TOPIC_MAP[key] || humanizeTopic(raw);
};

const normalizeTopicKey = (raw: string): string =>
  raw
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");

const normalizeDocTypeKey = (raw: string): string => {
  if (!raw) return "";
  const token = raw.split(".").pop() || raw;
  return token
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
};

const inferTopicKeysFromObligation = (item: Laws): string[] => {
  const text = `${item.must_do || ""} ${(item.summary_bullets || []).join(" ")} ${(item.conditions || "")}`.toLowerCase();
  const topics = new Set<string>();
  if (text.includes("ofac") || text.includes("sanction")) topics.add("sanctions");
  if (text.includes("suspicious activity") || text.includes("sar")) topics.add("aml_bsa");
  if (text.includes("currency transaction") || text.includes("ctr")) topics.add("ctr");
  if (text.includes("kyc") || text.includes("cip") || text.includes("customer due diligence")) topics.add("cdd_kyc");
  if (text.includes("beneficial owner")) topics.add("beneficial_ownership");
  if (text.includes("record") || text.includes("retain")) topics.add("recordkeeping");
  if (topics.size === 0) topics.add("aml_bsa");
  return Array.from(topics);
};

const normalizeJurisdictionLabel = (raw: string): string => {
  if (!raw) return "";
  const key = raw.replace(/[_-]+/g, " ").toLowerCase();
  if (key.includes("new jersey") || key === "nj" || key === "new jersey state") return "New Jersey";
  if (
    key.includes("federal") ||
    key === "us" ||
    key === "usa" ||
    key === "u.s." ||
    key.includes("united states")
  ) {
    return "Federal";
  }
  return key.replace(/\b\w/g, (c) => c.toUpperCase());
};

const buildSelectedTopicSet = (selected: string[]): Set<string> => {
  const canonical = new Set<string>();
  for (const topic of selected) {
    if (!topic) continue;
    const key = topic.trim().toLowerCase();
    const mapped = TOPIC_FILTER_MAP_NORMALIZED[key];
    if (mapped) {
      mapped.forEach((t) => canonical.add(t));
    } else {
      canonical.add(normalizeTopicKey(topic));
    }
  }
  return canonical;
};

const escapeHtml = (value: string) =>
  value.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

const renderHighlightedSnippet = (value: string): string => {
  if (!value) return "";
  const escaped = escapeHtml(value);
  return escaped
    .replace(/&lt;mark&gt;/g, "<mark>")
    .replace(/&lt;\/mark&gt;/g, "</mark>");
};

const normalizeArtifacts = (items: string[]): string[] => {
  const cleaned = items
    .map((value) => (value || "").trim())
    .filter((value) => value.length > 0);
  return Array.from(new Set(cleaned)).slice(0, 12);
};

const normalizeSentence = (value: string): string =>
  value.replace(/\s+/g, " ").trim();

const effectiveWhenApplies = (law: Laws): string => {
  const direct = normalizeSentence(law.conditions || "");
  if (direct.length > 0 && direct.toLowerCase() !== "not provided") return direct;

  const lower = (law.must_do || "").toLowerCase();
  for (const token of [" if ", " when ", " unless ", " upon "]) {
    const idx = lower.indexOf(token);
    if (idx >= 0) {
      return normalizeSentence((law.must_do || "").slice(idx + 1));
    }
  }
  return `Applies to entities and activities governed by ${law.citation}.`;
};

const formatConfidence = (value: number | null): string => {
  if (value === null || Number.isNaN(value)) return "N/A";
  return `${Math.round(value * 100)}%`;
};

const prettyReviewStatus = (value: string): string =>
  value.replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase());

const reviewStatusClass = (value: string): string => {
  const normalized = value.toLowerCase();
  if (normalized === "verified") return "bg-emerald-100 text-emerald-700 border-emerald-200";
  if (normalized === "deprecated") return "bg-rose-100 text-rose-700 border-rose-200";
  return "bg-amber-100 text-amber-700 border-amber-200";
};

export default function SearchPage() {
  // Raw input while typing (debounced before applying to searchQuery for filtering)
  const [rawSearchQuery, setRawSearchQuery] = useState("")
  const [searchQuery, setSearchQuery] = useState("")
  const [searched, setSearched] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  //filters
  const [selectedJurisdictions, setSelectedJurisdictions] = useState<string[]>(["Federal"])
  const [selectedAgencies, setSelectedAgencies] = useState<string[]>([])
  const [selectedDocTypes, setSelectedDocTypes] = useState<string[]>([])
  const [selectedTopics, setSelectedTopics] = useState<string[]>([])
  const [selectedChoice, setSelectedChoice] = useState<string>("Keyword")

  const [currentPage, setCurrentPage] = useState(1)
  const [copiedId, setCopiedId] = useState<string | null>(null)
  const searchInputRef = useRef<HTMLInputElement | null>(null)

  // TODO: Wire live results to UI; for now, suppress unused warning by not declaring until integrated
  const [fetchedLaws, setFetchedLaws] = useState<Laws[]>([])
  // Hydration-safe platform detection: first render matches server output.
  const [isMacPlatform, setIsMacPlatform] = useState(false)
  useEffect(() => {
    if (typeof navigator !== "undefined") {
      setIsMacPlatform(/Mac|iPhone|iPad/i.test(navigator.platform))
    }
  }, [])
  

  // Debounce utility (inline to avoid extra file)
  function useDebouncedValue<T>(value: T, delay: number): T {
    const [debounced, setDebounced] = useState(value)
    useEffect(() => {
      const handle = setTimeout(() => setDebounced(value), delay)
      return () => clearTimeout(handle)
    }, [value, delay])
    return debounced
  }

  const debouncedSearch = useDebouncedValue(rawSearchQuery, 250)

  // Apply debounced value to actual filtering state
  useEffect(() => {
    setSearchQuery(debouncedSearch)
    setCurrentPage(1)
  }, [debouncedSearch])

  // Keyboard shortcuts: Cmd/Ctrl+K focuses search, Escape clears
  useEffect(() => {
    function handler(e: KeyboardEvent) {
      const isCmdK = (e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k'
      if (isCmdK) {
        e.preventDefault()
        searchInputRef.current?.focus()
      } else if (e.key === 'Escape') {
        if (searchInputRef.current === document.activeElement) {
          setRawSearchQuery("")
        }
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  //handle search input change
  const onSearchChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setRawSearchQuery(e.target.value)
  }, [])

const fruitOptions = useMemo(
  () =>
    FRUIT_OPTIONS.map((f) => (
      <option key={f} value={f}>
        {f.charAt(0).toUpperCase() + f.slice(1)}
      </option>
    )),
  []
);


  const searchInputClass =
    "w-full pl-12 pr-4 py-3 md:py-4 text-base bg-card border-border/60 focus:border-accent placeholder:text-muted-foreground/60 hover:border-border/80 transition-colors"

  const resultsPerPage = 5
  const totalPages = Math.ceil(fetchedLaws.length / resultsPerPage)

  const fallbackCopyText = (text: string): boolean => {
    if (typeof document === "undefined") return false
    const textarea = document.createElement("textarea")
    textarea.value = text
    textarea.setAttribute("readonly", "")
    textarea.style.position = "fixed"
    textarea.style.opacity = "0"
    document.body.appendChild(textarea)
    textarea.focus()
    textarea.select()
    let copied = false
    try {
      copied = document.execCommand("copy")
    } catch {
      copied = false
    } finally {
      document.body.removeChild(textarea)
    }
    return copied
  }

  const handleCopyCitation = async (citation: string, url: string) => {
    const textToCopy = url ? `${citation}\n${url}` : citation
    let copied = false
    try {
      if (typeof navigator !== "undefined" && navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(textToCopy)
        copied = true
      } else {
        copied = fallbackCopyText(textToCopy)
      }
    } catch {
      copied = fallbackCopyText(textToCopy)
    }

    if (!copied) {
      console.warn("Clipboard copy is unavailable in this browser/context.")
      return
    }

    setCopiedId(url)
    setTimeout(() => setCopiedId(null), 2000)
  }

  const toggleFilter = (value: string, state: string[], setState: (items: string[]) => void) => {
    setState(state.includes(value) ? state.filter((item) => item !== value) : [...state, value])
    setCurrentPage(1)
  }

  const clearAllFilters = () => {
    setSearchQuery("")
    setSelectedJurisdictions([])
    setSelectedAgencies([])
    setSelectedDocTypes([])
    setSelectedTopics([])
    setCurrentPage(1)
  }

  const hasActiveFilters =
    searchQuery ||
    selectedJurisdictions.length > 0 ||
    selectedAgencies.length > 0 ||
    selectedDocTypes.length > 0 ||
    selectedTopics.length > 0

  //get AML Compliance topic from Elastic Search
  const fetchAMLComplianceTopic = async (query:string) => {
    setIsLoading(true);
    try {
      const response = await fetch(`/api/v1/law_search?query=${encodeURIComponent(query)}`, {
        method: "GET",
        cache: "no-store",
      });
      const payload = await response.json();
      //get status
      if (response.status === 500) {
        alert("You have exceeded the rate limit. Please try again later.");
        setFetchedLaws([]);
        return;
      }

      let data = payload?.data;
      if (!Array.isArray(data)) {
        console.warn("No data in response");
        setFetchedLaws([]);
        return;
      }
      //filter as per selected filters
      // Precompute Sets for O(1) membership checks
      const selAgencySet = new Set(selectedAgencies.map(a => a.toUpperCase()))
      const selTopicSet = buildSelectedTopicSet(selectedTopics)
      const selDocTypeSet = new Set(selectedDocTypes.map(normalizeDocTypeKey))

      const normalizeAgency = (raw: string): string => {
        if (!raw) return "";
        const token = raw.split(".").pop() || raw;
        const key = token.toLowerCase() as keyof typeof AGENCY_MAP;
        return (AGENCY_MAP[key] || token.toUpperCase()).toUpperCase();
      };

      data = data.filter((item: Laws) => {
        const jurisdictionLabel = normalizeJurisdictionLabel(item.jurisdiction);
        const matchesJurisdiction =
          selectedJurisdictions.length === 0 || selectedJurisdictions.includes(jurisdictionLabel);
        const agencyNorm = normalizeAgency(item.agency);
        const matchesAgency = selAgencySet.size === 0 || selAgencySet.has(agencyNorm);

        const itemTopics = inferTopicKeysFromObligation(item);
        const matchesTopic = selTopicSet.size === 0 || itemTopics.some((topic) => selTopicSet.has(topic));

        const itemDocType = normalizeDocTypeKey(item.instrument_type || "");
        const matchesDocType = selDocTypeSet.size === 0 || selDocTypeSet.has(itemDocType);

        return matchesJurisdiction && matchesAgency && matchesTopic && matchesDocType;
      })
      setFetchedLaws(data)  
    } catch (e) {
      console.warn("Failed to fetch AML Compliance topic", e)
      setFetchedLaws([])
    } finally {
      setSearched(true);
      setIsLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-background">

      {/* Main Content */}
      <main className="pt-12 pb-12 px-4">
        <div className="container mx-auto max-w-7xl">
          {/* Breadcrumb */}
          <div className="mb-8 text-sm text-muted-foreground">
            <Link href="/" className="hover:text-foreground transition-colors">
              ComplyAI
            </Link>
            <span className="mx-2">/</span>
            <span className="text-foreground">Regulatory Search</span>
          </div>

          {/* Header */}
          <div className="mb-12">
            <h1 className={"text-4xl md:text-5xl font-bold text-foreground mb-4 " + calSans.className}>Law Search</h1>
            <p className="text-lg text-muted-foreground">
              Search the complete regulatory library. Find exact CFR/NJAC clauses with clean snippets and full
              citations.
            </p>
          </div>

          {/* Search Bar (debounced, accessible, keyboard shortcut Cmd/Ctrl+K) */}
          <div className="mb-12">
            <div className="relative group flex gap-4 flex-col md:flex-row md:items-center">
              <div className="relative flex-1">
                <label htmlFor="reg-search" className="sr-only">Search regulations</label>
                <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground group-focus-within:text-accent transition-colors" />
                <Input
                  id="reg-search"
                  ref={searchInputRef}
                  type="text"
                  autoComplete="off"
                  aria-label="Search by keyword or citation"
                  placeholder="Search by keyword (e.g., 'AML') or citation (e.g., 31 CFR § 1010.230)..."
                  value={rawSearchQuery}
                  onChange={onSearchChange}
                  onKeyDown={async(event)=>{
                    if (event.key === "Enter") {
                      event.preventDefault();
                      await fetchAMLComplianceTopic(rawSearchQuery);
                    }
                  }}
                  className={searchInputClass}
                />
                {rawSearchQuery && (
                  <button
                    type="button"
                    onClick={() => setRawSearchQuery("")}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-xs px-2 py-1 rounded bg-muted hover:bg-muted/70 text-muted-foreground"
                    aria-label="Clear search"
                  >
                    Clear
                  </button>
                )}
              </div>
              <div className="w-full md:w-[200px]">
                      <div className="w-full flex flex-col gap-2">

      <div className="relative w-full">
        <select
          id="fruitChoice"
          value={selectedChoice || ""}
          onChange={(e) => setSelectedChoice(e.target.value)}
          className="
            block w-full appearance-none px-3 py-2 rounded-md border border-gray-300
            bg-white text-sm shadow-sm
            focus:outline-none focus:ring-2 focus:ring-emerald-500
            focus:border-emerald-500
          "
        >

          {/* Group Label */}
          <optgroup label="Choice">
            {fruitOptions}
          </optgroup>
        </select>

        {/* Chevron icon */}
        <span className="pointer-events-none absolute inset-y-0 right-3 flex items-center">
          <svg
            className="h-4 w-4 text-gray-500"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M19 9l-7 7-7-7"
            />
          </svg>
        </span>
      </div>
    </div>
              </div>
            </div>
            <div className="mt-2 text-xs text-muted-foreground flex flex-col gap-4">
              <p>
                <span>Press <kbd className="px-1 rounded bg-muted">{isMacPlatform ? 'RETURN ↵' : 'ENTER ↵'}</kbd> to search</span>
              </p>
            </div>
            
          </div>

          <div className="grid lg:grid-cols-4 gap-8">
            {/* Filter Sidebar */}
            <div className="lg:col-span-1">
              <Card className="border-border bg-card sticky top-24">
                <CardContent className="p-6">
                  <div className="flex items-center justify-between mb-6">
                    <h3 className="font-semibold text-foreground flex items-center gap-2">
                      <Filter className="w-4 h-4" />
                      Filters
                    </h3>
                    {hasActiveFilters && (
                      <button
                        onClick={clearAllFilters}
                        className="text-xs text-accent hover:text-accent/80 transition-colors font-medium"
                      >
                        Clear all
                      </button>
                    )}
                  </div>

                  <div className="space-y-6">
                    {/* Jurisdiction Filter */}
                    <div>
                      <h4 className="text-sm font-semibold text-foreground mb-3">Jurisdiction</h4>
                      <div className="space-y-2">
                        {JURISDICTIONS.map((jurisdiction) => (
                          <label key={jurisdiction} className="flex items-center gap-3 cursor-pointer group">
                            <input
                              type="checkbox"
                              checked={selectedJurisdictions.includes(jurisdiction)}
                              onChange={() =>
                                toggleFilter(jurisdiction, selectedJurisdictions, setSelectedJurisdictions)
                              }
                              className="w-4 h-4 rounded border-border accent-accent cursor-pointer"
                            />
                            <span className="text-sm text-muted-foreground group-hover:text-foreground transition-colors">
                              {jurisdiction}
                            </span>
                          </label>
                        ))}
                      </div>
                    </div>

                    {/* Agency Filter */}
                    <div>
                      <h4 className="text-sm font-semibold text-foreground mb-3">Agency</h4>
                      <div className="space-y-2 max-h-48 overflow-y-auto">
                        {AGENCIES.map((agency) => (
                          <label key={agency} className="flex items-center gap-3 cursor-pointer group">
                            <input
                              type="checkbox"
                              checked={selectedAgencies.includes(agency)}
                              onChange={() => toggleFilter(agency, selectedAgencies, setSelectedAgencies)}
                              className="w-4 h-4 rounded border-border accent-accent cursor-pointer"
                            />
                            <span className="text-sm text-muted-foreground group-hover:text-foreground transition-colors">
                              {agency}
                            </span>
                          </label>
                        ))}
                      </div>
                    </div>

                    {/* Document Type Filter */}
                    <div>
                      <h4 className="text-sm font-semibold text-foreground mb-3">Document Type</h4>
                      <div className="space-y-2">
                        {DOCUMENT_TYPES.map((docType) => (
                          <label key={docType} className="flex items-center gap-3 cursor-pointer group">
                            <input
                              type="checkbox"
                              checked={selectedDocTypes.includes(docType)}
                              onChange={() => toggleFilter(docType, selectedDocTypes, setSelectedDocTypes)}
                              className="w-4 h-4 rounded border-border accent-accent cursor-pointer"
                            />
                            <span className="text-sm text-muted-foreground group-hover:text-foreground transition-colors">
                              {docType}
                            </span>
                          </label>
                        ))}
                      </div>
                    </div>

                    {/* Topics Filter */}
                    <div>
                      <h4 className="text-sm font-semibold text-foreground mb-3">Topics</h4>
                      <div className="space-y-2 max-h-48 overflow-y-auto">
                        {TOPICS.map((topic) => (
                          <label key={topic} className="flex items-center gap-3 cursor-pointer group">
                            <input
                              type="checkbox"
                              checked={selectedTopics.includes(topic)}
                              onChange={() => toggleFilter(topic, selectedTopics, setSelectedTopics)}
                              className="w-4 h-4 rounded border-border accent-accent cursor-pointer"
                            />
                            <span className="text-sm text-muted-foreground group-hover:text-foreground transition-colors">
                              {topic}
                            </span>
                          </label>
                        ))}
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Results Section */}
            <div className="lg:col-span-3">
              {/* Results Header */}
              <div className="flex items-center justify-between mb-6">
                <div className="text-sm text-muted-foreground">
                  {fetchedLaws.length == 0 ? (
                   <p></p>
                  ) : (
                    <>
                      Showing{" "}
                      <span className="font-semibold text-foreground">{(currentPage - 1) * resultsPerPage + 1}</span>
                      {" to "}
                      <span className="font-semibold text-foreground">
                        {Math.min(currentPage * resultsPerPage, fetchedLaws.length)}
                      </span>
                      {" of "}
                      <span className="font-semibold text-foreground">{fetchedLaws.length}</span>
                      {" results"}
                    </>
                  )}
                </div>
              </div>

              {/* Results List */}
              {isLoading ? (
                <LoadingState />
              ) : (!searched) ? (
                <WelcomeState onQuickSearch={fetchAMLComplianceTopic} />
              ) : (fetchedLaws.length === 0 && searched) ? (
                <EmptyState />
              ) : (
                <div className="space-y-4">
                  {fetchedLaws.slice((currentPage - 1) * resultsPerPage, currentPage * resultsPerPage).map((law) => (
                    <Card
                      key={law.obligation_id || law.citation}
                      className="group overflow-hidden border-border/70 bg-card/95 transition-all duration-300 hover:-translate-y-0.5 hover:shadow-xl"
                    >
                      <CardContent className="p-0">
                        <div className="border-b border-border/60 bg-gradient-to-r from-accent/10 via-transparent to-transparent px-6 py-4">
                          <div className="flex items-start justify-between gap-4">
                            <div className="flex-1">
                              <p className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                                Obligation
                              </p>
                              <h3 className="text-base font-semibold text-accent transition-colors group-hover:text-accent/80 md:text-lg">
                                {law.citation}
                              </h3>
                              <p className="mt-1 text-sm font-medium text-foreground">{law.title}</p>
                            </div>
                            {/* <Badge
                              variant="secondary"
                              className={`hidden border px-2.5 py-1 text-[11px] font-semibold uppercase md:inline-flex ${reviewStatusClass(law.review_status)}`}
                            >
                              {prettyReviewStatus(law.review_status)}
                            </Badge> */}
                          </div>
                        </div>

                        <div className="space-y-4 p-6">
                          <div className="rounded-lg border border-border/60 bg-muted/25 p-4">
                            <p className="mb-2 flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                              <Scale className="h-3.5 w-3.5 text-accent" />
                              Must Do
                            </p>
                            <p className="text-sm font-medium leading-relaxed text-foreground">{law.must_do}</p>
                          </div>

                          <div className="grid gap-3 md:grid-cols-2">
                            <div className="rounded-lg border border-border/60 bg-muted/10 p-4">
                              <p className="mb-2 flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                                <Calendar className="h-3.5 w-3.5 text-accent" />
                                When It Applies
                              </p>
                              <p className="text-sm leading-relaxed text-muted-foreground">
                                {effectiveWhenApplies(law)}
                              </p>
                            </div>
                            <div className="rounded-lg border border-border/60 bg-muted/10 p-4">
                              <p className="mb-2 flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                                <FileCheck2 className="h-3.5 w-3.5 text-accent" />
                                Artifacts To Retain
                              </p>
                              <div className="flex flex-wrap gap-2">
                                {normalizeArtifacts(law.artifacts_required).length ? (
                                  normalizeArtifacts(law.artifacts_required).map((item) => (
                                    <Badge
                                      key={`${law.obligation_id}-artifact-${item}`}
                                      variant="secondary"
                                      className="border border-accent/30 bg-accent/10 text-[11px] font-semibold uppercase text-accent"
                                    >
                                      {item}
                                    </Badge>
                                  ))
                                ) : (
                                  <span className="text-sm text-muted-foreground">NOT PROVIDED</span>
                                )}
                              </div>
                            </div>
                          </div>

                          <div>
                            <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                              Excerpt (Highlighted)
                            </p>
                            <p
                              className="max-h-44 overflow-y-auto pr-1 text-sm leading-relaxed text-muted-foreground"
                              dangerouslySetInnerHTML={{
                                __html: renderHighlightedSnippet(law.excerpt || ""),
                              }}
                            />
                          </div>

                          {law.summary_bullets.length > 0 && (
                            <div>
                              <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                                Summary
                              </p>
                              <ul className="space-y-2">
                                {law.summary_bullets.slice(0, 3).map((bullet, idx) => (
                                  <li key={`${law.obligation_id}-${idx}`} className="flex items-start gap-2 text-sm text-muted-foreground">
                                    <span className="mt-0.5 inline-flex h-5 w-5 items-center justify-center rounded-full bg-accent/15 text-[11px] font-semibold text-accent">
                                      {idx + 1}
                                    </span>
                                    <span className="flex-1">{bullet}</span>
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}

                          <div className="flex flex-wrap gap-2">
                            <Badge variant="secondary" className="border border-border bg-muted text-xs uppercase text-muted-foreground">
                              {law.jurisdiction}
                            </Badge>
                            <Badge variant="secondary" className="border border-border bg-muted text-xs uppercase text-muted-foreground">
                              {law.agency}
                            </Badge>
                            <Badge variant="secondary" className="border border-border bg-muted text-xs uppercase text-muted-foreground">
                              {law.instrument_type}
                            </Badge>
                            <Badge
                              variant="secondary"
                              className={`border px-2 py-1 text-[11px] font-semibold uppercase md:hidden ${reviewStatusClass(law.review_status)}`}
                            >
                              {prettyReviewStatus(law.review_status)}
                            </Badge>
                          </div>

                          <div className="flex items-center justify-between border-t border-border/50 pt-4">
                            {/* <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                              <ShieldCheck className="h-3.5 w-3.5 text-accent" />
                              Confidence: {formatConfidence(law.confidence)}
                            </div> */}

                            <div className="flex items-center gap-2">
                              <span className="hidden items-center gap-1.5 text-xs text-muted-foreground md:inline-flex">
                                <Calendar className="h-3.5 w-3.5" />
                                Evidence-ready
                              </span>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleCopyCitation(law.citation, law.source_url)}
                              className={`gap-2 text-xs transition-all ${
                                copiedId === law.source_url 
                                  ? "bg-accent/10 text-accent"
                                  : "text-muted-foreground hover:text-foreground"
                              }`}
                            >
                              {copiedId === law.source_url ? (
                                <>
                                  <CheckCircle className="w-3.5 h-3.5" />
                                  Copied
                                </>
                              ) : (
                                <>
                                  <Copy className="w-3.5 h-3.5" />
                                  Copy Citation
                                </>
                              )}
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="gap-2 text-xs text-muted-foreground hover:text-foreground"
                              onClick={() => window.open(law.source_url, "_blank")}
                            >
                              <ExternalLink className="w-3.5 h-3.5" />
                              Open Source
                            </Button>
                            </div>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )}

              {/* Pagination */}
              {fetchedLaws.length > 0 && totalPages > 1 && (
                <div className="flex items-center justify-between mt-8">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                    disabled={currentPage === 1}
                    className="gap-2 border-border"
                  >
                    <ChevronLeft className="w-4 h-4" />
                    Previous
                  </Button>

                  <div className="flex items-center gap-2">
                    {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
                      <button
                        key={page}
                        onClick={() => setCurrentPage(page)}
                        className={`w-8 h-8 rounded text-sm font-medium transition-all ${
                          currentPage === page
                            ? "bg-accent text-accent-foreground"
                            : "text-muted-foreground hover:bg-muted hover:text-foreground"
                        }`}
                      >
                        {page}
                      </button>
                    ))}
                  </div>

                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
                    disabled={currentPage === totalPages}
                    className="gap-2 border-border"
                  >
                    Next
                    <ChevronRight className="w-4 h-4" />
                  </Button>
                </div>
              )}

              {/* Last Indexed Info (avoid hydration mismatch by client-side timestamp) */}
              <LastIndexedDisplay />
            </div>
          </div>
        </div>
      </main>
                    {/* Footer */}
      <footer className="bg-muted/30 border-t border-border py-6 px-4">
        <div className="container mx-auto">
          <div className="flex flex-col md:flex-row justify-between items-center gap-6">
          <Link href="/" className="ml-[-40px]">
        <Image src="/logo/comply-ai-logo.png" alt="aidoppel" width={100} height={100} />
        </Link>
            <div className="text-center text-muted-foreground text-sm">
              <p>
                &copy; 2025 <span className="text-accent font-medium">Comply AI</span>. All rights reserved.
              </p>
            </div>
            <div className="flex items-center gap-6 text-sm text-muted-foreground">
              <Link href="#" className="hover:text-foreground transition-colors">
                Privacy
              </Link>
              <Link href="#" className="hover:text-foreground transition-colors">
                Terms
              </Link>
              <Link href="#" className="hover:text-foreground transition-colors">
                Contact
              </Link>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}

// Separate component to prevent hydration mismatch due to dynamic Date rendering.
function LastIndexedDisplay() {
  const [display, setDisplay] = useState<string>("—");
  useEffect(() => {
    const d = new Date();
    // Locale formatting only after mount so server & client initial HTML match (placeholder)
    setDisplay(`${d.toLocaleDateString()} at ${d.toLocaleTimeString()}`);
  }, []);
  return (
    <div className="mt-8 p-4 bg-muted/30 border border-border/40 rounded-lg text-sm text-muted-foreground text-center">
      Database last indexed: {display}
    </div>
  );
}

type WelcomeStateProps = {
  onQuickSearch: (query: string) => Promise<void>
}

function WelcomeState({ onQuickSearch }: WelcomeStateProps) {
  const quickQueries = [
    "OFAC screening",
    "31 CFR 1020.320",
    "N.J.A.C. 3:15",
    "suspicious activity report",
  ]

  return (
    <Card className="relative overflow-hidden border-border/70 bg-gradient-to-br from-card via-card to-muted/40 p-6 md:p-8">
      <div className="absolute -right-12 -top-12 h-36 w-36 rounded-full bg-accent/10 blur-3xl" />
      <div className="absolute -left-10 bottom-0 h-28 w-28 rounded-full bg-primary/10 blur-2xl" />

      <div className="relative space-y-6">
        <div className="flex items-start gap-4">
          <div className="rounded-xl border border-border/60 bg-background/80 p-2.5">
            <Sparkles className="h-5 w-5 text-accent" />
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Law Search Workspace</p>
            <h3 className="mt-1 text-2xl font-semibold text-foreground">Welcome to Grounded Regulatory Search</h3>
            <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
              Query obligations by keyword or citation and get explainable results with citations, excerpts, required actions, and evidence-ready artifacts.
            </p>
          </div>
        </div>

        <div className="grid gap-3 md:grid-cols-3">
          <div className="rounded-xl border border-border/60 bg-background/70 p-4">
            <p className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-foreground">
              <BookOpenText className="h-4 w-4 text-accent" />
              Grounded Results
            </p>
            <p className="text-xs leading-relaxed text-muted-foreground">
              Every result is anchored to legal text excerpts, not just title-level matches.
            </p>
          </div>
          <div className="rounded-xl border border-border/60 bg-background/70 p-4">
            <p className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-foreground">
              <FileCheck2 className="h-4 w-4 text-accent" />
              Actionable Obligations
            </p>
            <p className="text-xs leading-relaxed text-muted-foreground">
              See what must be done, when it applies, and which artifacts should be retained.
            </p>
          </div>
          <div className="rounded-xl border border-border/60 bg-background/70 p-4">
            <p className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-foreground">
              <Search className="h-4 w-4 text-accent" />
              Fast Discovery
            </p>
            <p className="text-xs leading-relaxed text-muted-foreground">
              Combine filters with targeted queries across federal and New Jersey sources.
            </p>
          </div>
        </div>

        <div>
          <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Try a quick query</p>
          <div className="flex flex-wrap gap-2">
            {quickQueries.map((query) => (
              <Badge
                key={query}
                variant="secondary"
                role="button"
                tabIndex={0}
                onClick={() => void onQuickSearch(query)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault()
                    void onQuickSearch(query)
                  }
                }}
                className="cursor-pointer border border-border/60 bg-background/80 px-3 py-1.5 text-xs font-medium tracking-wide text-foreground hover:border-accent/40 hover:bg-accent/10"
              >
                {query}
              </Badge>
            ))}
          </div>
        </div>
      </div>
    </Card>
  )
}
