/**
 * Dispatch a tool result to the best renderer we have for that tool.
 *
 * The orchestrator forces response_format=json on Flowcase tools, so
 * the content blob is typed JSON. If parsing fails we fall back to a
 * plain pre-formatted block — no data is ever dropped silently.
 */

import AvailabilityResult from "./AvailabilityResult";
import FindUserResult from "./FindUserResult";
import FindUsersResult from "./FindUsersResult";
import GetCvResult from "./GetCvResult";
import ListOfficesResult from "./ListOfficesResult";
import ListRegionsResult from "./ListRegionsResult";
import ListSkillsResult from "./ListSkillsResult";
import SearchUsersResult from "./SearchUsersResult";
import type {
  AvailabilityResultData,
  CvData,
  FindUserData,
  FindUsersBySkillData,
  ListOfficesData,
  ListRegionsData,
  ListSkillsData,
  SearchUsersData,
} from "./types";

export function renderToolResult(name: string, content: string) {
  const parsed = tryParse(content);
  if (parsed === undefined) {
    // Not JSON — probably markdown or an error message.
    return (
      <pre className="max-h-64 overflow-auto whitespace-pre-wrap rounded bg-white p-2 text-[11px] text-slate-700">
        {content}
      </pre>
    );
  }

  switch (name) {
    case "flowcase_find_users_by_skill":
      return <FindUsersResult data={parsed as FindUsersBySkillData} />;
    case "flowcase_get_availability":
      return <AvailabilityResult data={parsed as AvailabilityResultData} />;
    case "flowcase_list_skills":
      return <ListSkillsResult data={parsed as ListSkillsData} />;
    case "flowcase_list_offices":
      if (Array.isArray(parsed))
        return <ListOfficesResult data={parsed as ListOfficesData} />;
      break;
    case "flowcase_list_regions":
      return <ListRegionsResult data={parsed as ListRegionsData} />;
    case "flowcase_find_user":
      return <FindUserResult data={parsed as FindUserData} />;
    case "flowcase_search_users":
      return <SearchUsersResult data={parsed as SearchUsersData} />;
    case "flowcase_get_cv":
      return <GetCvResult data={parsed as CvData} />;
  }

  return (
    <pre className="max-h-64 overflow-auto rounded bg-white p-2 text-[11px] text-slate-700">
      {JSON.stringify(parsed, null, 2)}
    </pre>
  );
}

function tryParse(content: string): unknown | undefined {
  const trimmed = content.trimStart();
  if (!trimmed || (!trimmed.startsWith("{") && !trimmed.startsWith("["))) {
    return undefined;
  }
  try {
    return JSON.parse(content);
  } catch {
    return undefined;
  }
}
