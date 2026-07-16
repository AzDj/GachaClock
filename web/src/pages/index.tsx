import { Accordion, AccordionItem } from '@heroui/react';
import { useEffect, useRef, useState } from 'react';

import {
  CardPool,
  type CardPoolProps,
  CountdownTimer,
  getHistoryEndTime,
  parseDateTime,
} from '@/components/card-pool';
import DefaultLayout from '@/layouts/default';
import {
  filterOpenedHistoryItems,
  isTimerAmbiguousAndUnexpired,
  isTimerOverlappingCurrentDate,
  isTimerStartedAndUnexpired,
} from '@/utils/history';
import { Link } from '@heroui/link';
import { useLocalStorage } from 'react-use';

const gameLabelMap: Record<string, string> = {
  sr: '崩铁',
  ww: '鸣潮',
  zzz: '绝区零',
  ys: '原神',
  arknights: '方舟',
  endfield: '终末地',
};
const imageLogoKeys = new Set(['sr', 'ww', 'zzz', 'ys', 'arknights', 'endfield']);
const newPoolVisibleDuration = 7 * 24 * 60 * 60 * 1000;

interface CurrentCardGroup {
  currentVersion: string;
  currentTimer: string;
  historyList: CardPoolProps['historyList'];
  hasNewPool: boolean;
}

export default function IndexPage() {
  const [cardGroup, setCardGroup] = useState<Record<string, CurrentCardGroup>>();
  const [storedExpandedKeys, setStoredExpandedKeys] = useLocalStorage<string[] | null>('expandedKeys', null);
  const [expandedKeys, setExpandedKeys] = useState<string[]>([]);
  const roleCache = useRef<Record<string, any>>({});

  useEffect(() => {
    const fetchData = async () => {
      const meta = await fetch('data/meta.json').then((res) => (res.ok ? res.json() : {}));

      console.log('meta:::', meta);

      await Promise.all(Object.keys(meta).map((game) => fetchEachGame(game, meta[game])));
    };

    fetchData();
  }, []);

  useEffect(() => {
    if (!cardGroup || Object.keys(cardGroup).length == 0) {
      return;
    }

    if (Array.isArray(storedExpandedKeys)) {
      setExpandedKeys(storedExpandedKeys);
      return;
    }

    setExpandedKeys(Object.keys(cardGroup));
  }, [cardGroup, storedExpandedKeys]);

  if (!cardGroup || Object.keys(cardGroup).length == 0) {
    return <div>Loading...</div>;
  }

  return (
    <DefaultLayout>
      <div>
        <Accordion
          selectedKeys={expandedKeys}
          selectionMode="multiple"
          variant="splitted"
          onSelectionChange={(keys) => {
            const nextExpandedKeys = keys === 'all' ? Object.keys(cardGroup) : [...keys].map(String);

            setExpandedKeys(nextExpandedKeys);
            setStoredExpandedKeys(nextExpandedKeys);
          }}
        >
          {Object.keys(cardGroup)
            .sort((a, b) => {
              const endDiff = getHistoryEndTime(cardGroup[a].currentTimer) - getHistoryEndTime(cardGroup[b].currentTimer);
              return endDiff || a.localeCompare(b);
            })
            .map((key) => (
              <AccordionItem
                key={key}
                aria-label={cardGroup[key].currentVersion}
                startContent={renderGameLogo(key)}
                subtitle={
                  <CountdownTimer
                    className={'text-lg'}
                    date={cardGroup[key].currentTimer.split('~')[1]}
                    prefix={renderGameName(key, cardGroup[key].hasNewPool)}
                  />
                }
                indicator={({ isOpen }) => <Link href={`/history/${key}`}>H</Link>}
              >
                <CardPool historyList={cardGroup[key].historyList} />
              </AccordionItem>
            ))}
        </Accordion>
      </div>
    </DefaultLayout>
  );

  function renderGameLogo(key: string) {
    const normalizedKey = key.toLocaleLowerCase();

    if (imageLogoKeys.has(normalizedKey)) {
      return (
        <img
          alt="Logo"
          className="w-10 h-10 rounded-full"
          src={`${normalizedKey}.png`}
        />
      );
    }

    return (
      <div className="w-10 h-10 rounded-full bg-default-200 text-default-700 flex items-center justify-center text-xs font-medium">
        {gameLabelMap[normalizedKey] ?? key}
      </div>
    );
  }

  function renderGameName(key: string, hasNewPool: boolean) {
    const normalizedKey = key.toLocaleLowerCase();

    return (
      <>
        <span className="font-medium text-foreground">{gameLabelMap[normalizedKey] ?? key}</span>
        {hasNewPool && (
          <span className="rounded-small bg-orange-100 px-1.5 py-0.5 text-[11px] font-semibold leading-none text-orange-600 dark:bg-orange-500/20 dark:text-orange-300">
            new
          </span>
        )}
      </>
    );
  }

  async function fetchEachGame(key: string, lastPoolUrl: string) {
    const role = await fetchEachGameRole(key);
    console.log(`${key} role`, role);

    let historyList: any[];
    let version: string;
    let timer: string;
    let roleKey: string; // 历史卡池为 s，meta信息为title
    let hasNewPool = false;

    try {
      roleKey = 's';
      const data = await fetch(`data/${key}/history.json`).then((res) => res.json());
      console.log(`${key} history`, data);

      const selectedHistoryList = selectCurrentHistoryList(filterOpenedHistoryItems(data), key);
      historyList = normalizeHistoryList(selectedHistoryList);

      if (historyList.length === 0) {
        throw new Error('没有当前历史卡池');
      }

      const nearestHistoryItem = selectNearestCurrentHistoryItem(selectedHistoryList);
      version = nearestHistoryItem.version;
      timer = nearestHistoryItem.timer;
      hasNewPool = await resolveHistoryNewPoolFlag(selectedHistoryList, timer, lastPoolUrl);
    } catch (err) {
      console.log(`${key} history err, 使用最新卡池数据, 即从meta里面获取。 `, err);

      const data = await fetch(lastPoolUrl).then((res) => res.json());
      console.log(`${key} meta`, data);

      if (data[0]?.gachas) {
        roleKey = 'title';

        if (!role || Object.keys(role).length === 0) {
          historyList = data
            .filter((item: any) => item.type === '角色')
            .map((item: any) => item.gachas[0]);
        } else {
          historyList = data
            .filter((item: any) => item.type === '角色')
            .flatMap((item: any) => item.gachas)
            .filter(
              (item: any) => !role?.[item['title']] || role?.[item['title']].chara_rarity === '5星',
            );
        }

        const timerSource = selectCurrentMetaTimer(data);
        version = timerSource.title;
        timer = timerSource.timer.join('~');
        hasNewPool = isRecentNewPool(timer);
      } else {
        roleKey = 's';
        const selectedHistoryList = selectCurrentHistoryList(filterOpenedHistoryItems(data), key);
        historyList = normalizeHistoryList(selectedHistoryList);

        if (historyList.length === 0) {
          throw new Error('meta 历史卡池为空');
        }

        const nearestHistoryItem = selectNearestCurrentHistoryItem(selectedHistoryList);
        version = nearestHistoryItem.version;
        timer = nearestHistoryItem.timer;
        hasNewPool = await resolveHistoryNewPoolFlag(selectedHistoryList, timer, lastPoolUrl);
      }
    }

    historyList.forEach((item) => {
      const roleName = Array.isArray(item[roleKey]) ? item[roleKey][0] : item[roleKey];
      const promotionImg = role?.[roleName]?.['promotion_img'];
      const simpleImg = role?.[roleName]?.['simple_img'];
      const cachedImg = normalizeAssetUrl(item['img_path']);
      const sourceImg = item['img'];

      if (roleKey === 's') {
        item['img'] = cachedImg || sourceImg || promotionImg?.[1] || promotionImg?.[0] || simpleImg;
        return;
      }

      item['img'] = promotionImg?.[1] || promotionImg?.[0] || cachedImg || sourceImg || simpleImg;
    });

    console.log(`${key} historyList::`, historyList);

    setCardGroup((prev: any) => ({
      ...prev,
      [key]: {
        currentVersion: version,
        currentTimer: timer,
        historyList: historyList,
        hasNewPool,
      },
    }));
  }

  function selectCurrentHistoryList(data: any[], key: string) {
    if (!data || data.length === 0) {
      return [];
    }

    const currentTime = new Date().getTime();
    const finiteCurrentList = data.filter((item: any) => isTimerStartedAndUnexpired(item.timer, currentTime));

    if (finiteCurrentList.length > 0) {
      return finiteCurrentList;
    }

    const currentDateList = key === 'arknights'
      ? data.filter((item: any) => isTimerOverlappingCurrentDate(item.timer, currentTime))
      : [];

    if (currentDateList.length > 0) {
      return currentDateList;
    }

    const ambiguousCurrentList = data.filter((item: any) => isTimerAmbiguousAndUnexpired(item.timer, currentTime));

    return ambiguousCurrentList;
  }

  function selectNearestCurrentHistoryItem(data: any[]) {
    const currentTime = new Date().getTime();
    const unexpiredList = data.filter((item: any) => {
      const endTime = getHistoryEndTime(item.timer);

      return currentTime <= endTime;
    });

    return selectNearestHistoryItem(unexpiredList.length > 0 ? unexpiredList : data);
  }

  function selectNearestHistoryItem(data: any[]) {
    return [...data].sort((a: any, b: any) => {
      const endDiff = getHistoryEndTime(a.timer) - getHistoryEndTime(b.timer);
      return endDiff || `${a.title}`.localeCompare(`${b.title}`);
    })[0];
  }

  function selectCurrentMetaTimer(data: any[]) {
    const currentTime = new Date().getTime();
    const currentList = data
      .map((item: any) => ({ item, range: getMetaTimerRange(item.timer) }))
      .filter(({ range }) => Number.isFinite(range.start) && Number.isFinite(range.end) && range.start <= currentTime && currentTime <= range.end)
      .sort((a, b) => a.range.end - b.range.end);

    return (currentList[0]?.item ?? data[data.length - 1]) as any;
  }

  function normalizeHistoryList(data: any[]) {
    const roleList = data.filter((item: any) => item.type === '角色');
    const sourceList = roleList.length > 0 ? roleList : data;

    return sourceList.map((item: any) => {
      const copy = { ...item };
      const titleEndIndex = typeof item.title === 'string' ? item.title.indexOf('」') : -1;

      if (titleEndIndex >= 0) {
        copy.title = item.title.substring(0, titleEndIndex + 1);
      }

      return copy;
    });
  }

  function getMetaTimerRange(timer: string[]) {
    return {
      start: parseDateTime(timer?.[0]),
      end: parseDateTime(timer?.[1]),
    };
  }

  function normalizeAssetUrl(value?: string) {
    if (!value) {
      return '';
    }

    if (/^https?:\/\//.test(value) || value.startsWith('/')) {
      return value;
    }

    return `/${value}`;
  }

  async function resolveHistoryNewPoolFlag(data: any[], fallbackTimer: string, lastPoolUrl: string) {
    const finiteStartList = data
      .map((item: any) => getPoolStartTime(`${item.timer ?? ''}`))
      .filter(Number.isFinite);

    if (finiteStartList.length > 0) {
      return finiteStartList.some((startTime) => isRecentStartTime(startTime));
    }

    if (isRecentNewPool(fallbackTimer)) {
      return true;
    }

    return resolveLatestMetaNewPoolFlag(fallbackTimer, lastPoolUrl);
  }

  async function resolveLatestMetaNewPoolFlag(fallbackTimer: string, lastPoolUrl: string) {
    try {
      const data = await fetch(lastPoolUrl).then((res) => res.json());
      const latestTimer = normalizeMetaTimer(selectCurrentMetaTimer(data)?.timer);

      if (!latestTimer || !isSamePoolEndTime(fallbackTimer, latestTimer)) {
        return false;
      }

      return isRecentNewPool(latestTimer);
    } catch (err) {
      console.log('无法确认最新卡池更新时间，隐藏 new 标记。', err);
      return false;
    }
  }

  function normalizeMetaTimer(timer: string[] | string | undefined) {
    if (Array.isArray(timer)) {
      return timer.join('~');
    }

    return timer ?? '';
  }

  function isSamePoolEndTime(leftTimer: string, rightTimer: string) {
    const leftEndTime = getHistoryEndTime(leftTimer);
    const rightEndTime = getHistoryEndTime(rightTimer);

    return Number.isFinite(leftEndTime)
      && Number.isFinite(rightEndTime)
      && Math.abs(leftEndTime - rightEndTime) < 60 * 1000;
  }

  function isRecentNewPool(timer: string) {
    return isRecentStartTime(getPoolStartTime(timer));
  }

  function getPoolStartTime(timer: string) {
    const startTimer = `${timer ?? ''}`.split('~')[0];

    return parseDateTime(startTimer);
  }

  function isRecentStartTime(startTime: number) {
    const currentTime = new Date().getTime();

    return Number.isFinite(startTime)
      && startTime <= currentTime
      && currentTime < startTime + newPoolVisibleDuration;
  }

  async function fetchEachGameRole(key: string) {
    if (roleCache.current[key]) {
      console.log(`${key} 使用缓存的 role 数据`);
      return roleCache.current[key];
    }

    return fetch(`data/${key}/role.json`)
      .then((res) => res.json())
      .then((data) => {
        // console.log(`${key} role`, data);
        const tmp_role = data.reduce((acc, item) => {
          acc[item.title] = item;
          return acc;
        }, {});
        roleCache.current[key] = tmp_role;
        return tmp_role;
      })
      .catch((err) => {
        console.log(`${key} 无法获取角色信息，返回空.`, err);
        roleCache.current[key] = {};
        return {};
      });
  }
}
