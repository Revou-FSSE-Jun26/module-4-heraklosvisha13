export const ORDER_STEP = 1000;

/**
 * FLOAT order for an item inserted at `index` among `siblings`
 * (siblings are sorted ascending and exclude the moved item).
 */
export function computeOrder(siblings: { order: number }[], index: number): number {
  if (siblings.length === 0) return ORDER_STEP;
  if (index <= 0) return siblings[0].order / 2;
  if (index >= siblings.length) return siblings[siblings.length - 1].order + ORDER_STEP;
  return (siblings[index - 1].order + siblings[index].order) / 2;
}
