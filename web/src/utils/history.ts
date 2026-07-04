import { parseDateTime } from '@/components/card-pool';

export function getTimerRange(timer: string) {
  const [startTimer, endTimer] = `${timer ?? ''}`.split('~');

  return {
    start: parseDateTime(startTimer),
    end: parseDateTime(endTimer),
  };
}

export function filterOpenedHistoryItems<T extends { timer?: string; version?: string; title?: string }>(
  data: T[],
  currentTime = new Date().getTime(),
) {
  const groupMap = data.reduce<Record<string, T[]>>((groups, item) => {
    const groupKey = `${item.version || item.title || 'unknown'}`;

    groups[groupKey] = groups[groupKey] || [];
    groups[groupKey].push(item);

    return groups;
  }, {});
  const openedGroupKeys = new Set(
    Object.entries(groupMap)
      .filter(([, historyList]) => isVersionGroupOpened(historyList, currentTime))
      .map(([groupKey]) => groupKey),
  );

  return data.filter((item) => openedGroupKeys.has(`${item.version || item.title || 'unknown'}`));
}

export function isTimerStartedAndUnexpired(timer: string, currentTime: number) {
  const { start, end } = getTimerRange(timer);

  return Number.isFinite(start) && start <= currentTime && (!Number.isFinite(end) || currentTime <= end);
}

export function isTimerAmbiguousAndUnexpired(timer: string, currentTime: number) {
  const { start, end } = getTimerRange(timer);

  return !Number.isFinite(start) && Number.isFinite(end) && currentTime <= end;
}

export function getVersionFamily(version: string) {
  const match = `${version ?? ''}`.match(/(\d+)\.(\d+)/);

  if (!match) {
    return '其他';
  }

  return `${match[1]}.x`;
}

export function compareVersionFamilyDesc(left: string, right: string) {
  return getFamilySortValue(right) - getFamilySortValue(left) || right.localeCompare(left);
}

export function compareVersionDesc(left: string, right: string) {
  const rightValue = getVersionSortValue(right);
  const leftValue = getVersionSortValue(left);

  return rightValue - leftValue || right.localeCompare(left);
}

function isVersionGroupOpened<T extends { timer?: string }>(historyList: T[], currentTime: number) {
  const finiteStartList = historyList
    .map((item) => getTimerRange(`${item.timer ?? ''}`).start)
    .filter(Number.isFinite);

  if (finiteStartList.length === 0) {
    return true;
  }

  return Math.min(...finiteStartList) <= currentTime;
}

function getFamilySortValue(versionFamily: string) {
  const match = `${versionFamily ?? ''}`.match(/^(\d+)\.x$/);

  return match ? Number(match[1]) : Number.NEGATIVE_INFINITY;
}

function getVersionSortValue(version: string) {
  const match = `${version ?? ''}`.match(/(\d+)\.(\d+)/);

  if (!match) {
    return Number.NEGATIVE_INFINITY;
  }

  return Number(match[1]) * 1000 + Number(match[2]) * 10 + getPhaseSortValue(version);
}

function getPhaseSortValue(version: string) {
  if (version.includes('下半')) {
    return 3;
  }
  if (version.includes('额外')) {
    return 2;
  }
  if (version.includes('上半')) {
    return 1;
  }

  return 0;
}
