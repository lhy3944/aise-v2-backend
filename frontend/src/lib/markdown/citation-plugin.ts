// `unified`의 `Plugin<Parameters, Tree>` 타입은 직접 임포트 불가(transitive
// 의존성이라 strict pnpm에서 해결 안 됨). Streamdown은 PluggableList만 요구하고
// PluggableList는 (Plugin | [Plugin, ...options] | ...) 형태이므로, 여기서는
// unified에 호환되는 최소 형태 — `() => (tree) => tree | void` — 를 수작업 정의한다.
type RehypeTransformer = (tree: HastNode) => HastNode | void;
type RehypePlugin = () => RehypeTransformer;

interface HastText {
  type: 'text';
  value: string;
}

interface HastElement {
  type: 'element';
  tagName: string;
  properties?: Record<string, unknown>;
  children: HastNode[];
}

interface HastRoot {
  type: 'root';
  children: HastNode[];
}

type HastNode = HastText | HastElement | HastRoot | { type: string; children?: HastNode[] };

const CITATION_RE = /\[(\d+)\]/g;
const SKIP_TAGS = new Set(['code', 'pre']);

function isElement(node: HastNode): node is HastElement {
  return node.type === 'element';
}

function isText(node: HastNode): node is HastText {
  return node.type === 'text';
}

/**
 * hast tree의 모든 text 노드를 순회하며 `[N]` 패턴을
 * `<span data-citation-ref="N">[N]</span>` 요소로 치환한다.
 *
 * allowedRefs에 포함된 번호만 치환하고, 나머지는 원본 텍스트를 유지한다.
 * `<code>` · `<pre>` 하위 텍스트는 건너뛴다.
 *
 * 매 렌더에서 새 플러그인 인스턴스를 만들면 AST 레벨 변환이 안정적으로
 * 적용되어 Streamdown의 스트리밍 재렌더에도 span이 사라지지 않는다.
 */
export function createCitationPlugin(allowedRefs: Set<number>): RehypePlugin {
  if (allowedRefs.size === 0) {
    return () => (tree: HastNode) => tree;
  }

  return () => {
    function walk(parent: HastElement | HastRoot): void {
      if (!parent.children || parent.children.length === 0) return;
      const next: HastNode[] = [];

      for (const child of parent.children) {
        if (isElement(child)) {
          if (SKIP_TAGS.has(child.tagName)) {
            next.push(child);
            continue;
          }
          walk(child);
          next.push(child);
          continue;
        }

        if (!isText(child)) {
          next.push(child);
          continue;
        }

        const text = child.value;
        if (!text || !CITATION_RE.test(text)) {
          next.push(child);
          continue;
        }

        CITATION_RE.lastIndex = 0;
        let lastIdx = 0;
        let matched = false;

        for (const m of text.matchAll(CITATION_RE)) {
          const ref = Number(m[1]);
          if (!allowedRefs.has(ref)) continue;
          matched = true;

          const matchIdx = m.index ?? 0;
          if (matchIdx > lastIdx) {
            next.push({ type: 'text', value: text.slice(lastIdx, matchIdx) });
          }
          next.push({
            type: 'element',
            tagName: 'span',
            properties: {
              dataCitationRef: String(ref),
              className: ['citation-inline'],
            },
            children: [{ type: 'text', value: m[0] }],
          });
          lastIdx = matchIdx + m[0].length;
        }

        if (!matched) {
          next.push(child);
          continue;
        }

        if (lastIdx < text.length) {
          next.push({ type: 'text', value: text.slice(lastIdx) });
        }
      }

      parent.children = next;
    }

    return (tree: HastNode) => {
      if ('children' in tree && Array.isArray(tree.children)) {
        walk(tree as HastRoot);
      }
      return tree;
    };
  };
}
