/** PlantUML 텍스트를 이미지 URL로 변환하는 유틸리티. */

const PLANTUML_SERVER =
  process.env.NEXT_PUBLIC_PLANTUML_SERVER ?? 'https://www.plantuml.com/plantuml';

/** PlantUML 텍스트에서 ```plantuml ... ``` 블록을 추출. */
export function extractPlantUmlBlocks(content: string): string[] {
  const blocks: string[] = [];
  const regex = /```plantuml\s*\n([\s\S]*?)```/gi;
  let match: RegExpExecArray | null;
  while ((match = regex.exec(content)) !== null) {
    blocks.push(match[1].trim());
  }
  return blocks;
}

/** 다크 테마용 PlantUML skinparam 지시어. */
const DARK_SKIN_PARAMS = `
skinparam backgroundColor transparent
skinparam shadowing false
skinparam defaultFontColor #E0E0E0
skinparam defaultFontSize 14
skinparam ArrowColor #9E9E9E
skinparam RectangleBorderColor #9E9E9E
skinparam RectangleBackgroundColor #2A2A2A
skinparam RectangleFontColor #E0E0E0
skinparam ClassBorderColor #9E9E9E
skinparam ClassBackgroundColor #2A2A2A
skinparam ClassFontColor #E0E0E0
skinparam EntityBorderColor #9E9E9E
skinparam EntityBackgroundColor #2A2A2A
skinparam EntityFontColor #E0E0E0
skinparam UseCaseBorderColor #9E9E9E
skinparam UseCaseBackgroundColor #2A2A2A
skinparam UseCaseFontColor #E0E0E0
skinparam ActorBorderColor #9E9E9E
skinparam ActorFontColor #E0E0E0
skinparam ActorStyle awesome
skinparam NoteBorderColor #9E9E9E
skinparam NoteFontColor #E0E0E0
skinparam NoteBackgroundColor #2A2A2A
skinparam PackageBorderColor #9E9E9E
skinparam PackageBackgroundColor #1E1E1E
skinparam PackageFontColor #E0E0E0
skinparam ComponentBorderColor #9E9E9E
skinparam ComponentBackgroundColor #2A2A2A
skinparam ComponentFontColor #E0E0E0
skinparam InterfaceBorderColor #9E9E9E
skinparam SequenceMessageColor #E0E0E0
skinparam SequenceLifeLineBorderColor #9E9E9E
skinparam SequenceParticipantBorderColor #9E9E9E
skinparam SequenceParticipantBackgroundColor #2A2A2A
skinparam SequenceParticipantFontColor #E0E0E0
skinparam PartitionBorderColor #9E9E9E
skinparam PartitionBackgroundColor #2A2A2A
skinparam PartitionFontColor #E0E0E0
skinparam ActivityBorderColor #9E9E9E
skinparam ActivityBackgroundColor #2A2A2A
skinparam ActivityFontColor #E0E0E0
skinparam ActivityDiamondBorderColor #9E9E9E
skinparam ActivityDiamondBackgroundColor #2A2A2A
skinparam ActivityDiamondFontColor #E0E0E0
skinparam ConditionStyle diamond
`;

/** PlantUML 코드에 다크 테마 skinparam을 주입.
 *  @startuml 바로 다음 줄에 skinparam을 삽입.
 */
function injectDarkTheme(code: string): string {
  return code.replace(/@startuml/i, (match) => `${match}\n${DARK_SKIN_PARAMS}`);
}

/** PlantUML 텍스트를 deflate + Base64 인코딩하여 이미지 URL 생성.
 *  @param dark 다크 테마 여부 (true 시 배경 투명 + 라이트 컬러 skinparam 주입)
 */
export async function plantumlImageUrl(
  plantumlCode: string,
  { dark = false }: { dark?: boolean } = {},
): Promise<string> {
  const code = dark ? injectDarkTheme(plantumlCode) : plantumlCode;
  try {
    const { encode } = await import('plantuml-encoder');
    const encoded = encode(code);
    return `${PLANTUML_SERVER}/svg/${encoded}`;
  } catch {
    const encoded = btoa(unescape(encodeURIComponent(code)));
    return `${PLANTUML_SERVER}/txt/${encoded}`;
  }
}
