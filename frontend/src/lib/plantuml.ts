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

/** 라이트 테마용 PlantUML skinparam 지시어. 패널 배경(#f5f5f7)에 어우러는 톤. */
const LIGHT_SKIN_PARAMS = `
skinparam backgroundColor #F5F5F7
skinparam shadowing false
skinparam defaultFontColor #171717
skinparam defaultFontSize 14
skinparam ArrowColor #60646C
skinparam RectangleBorderColor #BFC1C7
skinparam RectangleBackgroundColor #FFFFFF
skinparam RectangleFontColor #171717
skinparam ClassBorderColor #BFC1C7
skinparam ClassBackgroundColor #FFFFFF
skinparam ClassFontColor #171717
skinparam EntityBorderColor #BFC1C7
skinparam EntityBackgroundColor #FFFFFF
skinparam EntityFontColor #171717
skinparam UseCaseBorderColor #BFC1C7
skinparam UseCaseBackgroundColor #FFFFFF
skinparam UseCaseFontColor #171717
skinparam ActorBorderColor #60646C
skinparam ActorFontColor #171717
skinparam ActorStyle awesome
skinparam NoteBorderColor #BFC1C7
skinparam NoteFontColor #4A4C52
skinparam NoteBackgroundColor #F0F0F3
skinparam PackageBorderColor #BFC1C7
skinparam PackageBackgroundColor #E8E9ED
skinparam PackageFontColor #171717
skinparam ComponentBorderColor #BFC1C7
skinparam ComponentBackgroundColor #FFFFFF
skinparam ComponentFontColor #171717
skinparam InterfaceBorderColor #BFC1C7
skinparam SequenceMessageColor #171717
skinparam SequenceLifeLineBorderColor #BFC1C7
skinparam SequenceParticipantBorderColor #BFC1C7
skinparam SequenceParticipantBackgroundColor #FFFFFF
skinparam SequenceParticipantFontColor #171717
skinparam PartitionBorderColor #BFC1C7
skinparam PartitionBackgroundColor #F0F0F3
skinparam PartitionFontColor #171717
skinparam ActivityBorderColor #BFC1C7
skinparam ActivityBackgroundColor #FFFFFF
skinparam ActivityFontColor #171717
skinparam ActivityDiamondBorderColor #BFC1C7
skinparam ActivityDiamondBackgroundColor #F0F0F3
skinparam ActivityDiamondFontColor #171717
skinparam ConditionStyle diamond
`;

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

/** 라이트 테마 코드에 skinparam 주입. */
function injectLightTheme(code: string): string {
  return code.replace(/@startuml/i, (match) => `${match}\n${LIGHT_SKIN_PARAMS}`);
}

/** PlantUML 텍스트를 deflate + Base64 인코딩하여 이미지 URL 생성.
 *  @param dark 다크 테마 여부 (true 시 다크 스킨, false 시 라이트 스킨 주입)
 */
export async function plantumlImageUrl(
  plantumlCode: string,
  { dark = false }: { dark?: boolean } = {},
): Promise<string> {
  const code = dark ? injectDarkTheme(plantumlCode) : injectLightTheme(plantumlCode);
  try {
    const { encode } = await import('plantuml-encoder');
    const encoded = encode(code);
    return `${PLANTUML_SERVER}/svg/${encoded}`;
  } catch {
    const encoded = btoa(unescape(encodeURIComponent(code)));
    return `${PLANTUML_SERVER}/txt/${encoded}`;
  }
}
