/**
 * Artifact governance 하의 TestCase payload 타입.
 *
 * 백엔드 [schemas/api/artifact_testcase.py](../../backend/src/schemas/api/artifact_testcase.py)
 * 의 `TestCaseContent` 와 1:1 동기화.
 */

export type TestCasePriority = 'high' | 'medium' | 'low';
export type TestCaseType =
  | 'functional'
  | 'non_functional'
  | 'boundary'
  | 'negative';

export interface TestCaseContent {
  title: string;
  precondition: string;
  steps: string[];
  expected_result: string;
  priority: TestCasePriority;
  type: TestCaseType;
  related_srs_section_id: string | null;
}
