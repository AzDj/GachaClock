import { CardPool } from '@/components/card-pool';
import DefaultLayout from '@/layouts/default';
import {
  compareVersionDesc,
  compareVersionFamilyDesc,
  filterOpenedHistoryItems,
  getVersionFamily,
} from '@/utils/history';
import { Accordion, AccordionItem } from '@heroui/react';
import { groupBy } from 'lodash';
import { useEffect, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useLocalStorage } from 'react-use';

export default function HistoryPage() {
  const [cardGroup, setCardGroup] = useState<Record<string, Record<string, any[]>>>({});
  const [titleMap, setTitleMap] = useState<Record<string, string>>({});
  const [expandedFamilyKeys, setExpandedFamilyKeys] = useLocalStorage<string[] | null>('history/expandedFamilyKeys', null);
  const [expandedVersionKeyMap, setExpandedVersionKeyMap] = useLocalStorage<Record<string, string[]> | null>(
    'history/expandedVersionKeyMap',
    null,
  );
  const roleCache = useRef<Record<string, any>>({});

  let { key } = useParams();

  console.log('key:::', key);

  useEffect(() => {
    if (!key) {
      return;
    }

    const fetchData = async () => {
      let role = await fetchEachGameRole(key);

      fetch(`/data/${key}/history.json`)
        .then((res) => res.json())
        .then((data) => {
          console.log('data:::', data);
          data.forEach((element) => {
            element.img_path = normalizeAssetUrl(element.img_path);
          });
          const openedHistoryList = filterOpenedHistoryItems(data as any[]);
          let versionGroup = groupBy(openedHistoryList, 'version') as Record<string, any[]>;
          console.log('versionGroup:::', versionGroup);

          const nextTitleMap: Record<string, string> = {};

          Object.keys(versionGroup).forEach((key) => {
            // 卡池图片没有的时候，使用角色立绘
            // console.log(`key::: ${key}`, versionGroup[key]);
            versionGroup[key].forEach((item) => {
              // console.log(`item::: ${item.s}`, item);
              console.log(`role::: ${key}`, role);
              const roleName = Array.isArray(item['s']) ? item['s'][0] : item['s'];
              const promotionImg = role?.[roleName]?.['promotion_img'];
              const simpleImg = role?.[roleName]?.['simple_img'];
              item['img'] = promotionImg?.[1] || promotionImg?.[0] || item['img_path'] || item['img'] || simpleImg;
            });

            // 没有图片的再排除
            versionGroup[key] = versionGroup[key].filter((item) => item.img !== '' && item.img);

            // 设置title
            const roleNames = versionGroup[key]
              .filter((item) => item.type === '角色')
              .flatMap((item) => (Array.isArray(item.s) ? item.s : [item.s]))
              .filter(Boolean);
            const fallbackNames = versionGroup[key]
              .flatMap((item) => (Array.isArray(item.s) ? item.s : [item.s || item.title]))
              .filter(Boolean);
            const displayNames = roleNames.length > 0 ? roleNames : fallbackNames;

            nextTitleMap[key] = `${versionGroup[key][0]?.timer ?? ''} ${displayNames.join('、')}`.trim();
          });
          const nextCardGroup = Object.keys(versionGroup).reduce<Record<string, Record<string, any[]>>>(
            (groups, versionKey) => {
              const versionFamily = getVersionFamily(versionKey);

              groups[versionFamily] = groups[versionFamily] || {};
              groups[versionFamily][versionKey] = versionGroup[versionKey];

              return groups;
            },
            {},
          );

          setCardGroup(nextCardGroup);
          setTitleMap(nextTitleMap);
        });
    };

    fetchData();
  }, []);

  async function fetchEachGameRole(key: string) {
    if (roleCache.current[key]) {
      console.log(`${key} 使用缓存的 role 数据`);
      return roleCache.current[key];
    }

    return fetch(`/data/${key}/role.json`)
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

  function normalizeAssetUrl(value?: string) {
    if (!value) {
      return '';
    }

    if (/^https?:\/\//.test(value) || value.startsWith('/')) {
      return value;
    }

    return `/${value}`;
  }

  return (
    <DefaultLayout>
      <div>
        <Accordion
          selectedKeys={getSelectedFamilyKeys()}
          selectionMode="multiple"
          variant="splitted"
          onSelectionChange={(keys) => {
            setExpandedFamilyKeys(resolveSelectionKeys(keys, getVersionFamilyKeys()));
          }}
        >
          {getVersionFamilyKeys().map((versionFamily) => (
            <AccordionItem
              key={versionFamily}
              aria-label={versionFamily}
              startContent={versionFamily}
              subtitle={getVersionFamilySubtitle(versionFamily)}
            >
              <Accordion
                selectedKeys={getSelectedVersionKeys(versionFamily)}
                selectionMode="multiple"
                variant="splitted"
                onSelectionChange={(keys) => {
                  setExpandedVersionKeyMap({
                    ...(expandedVersionKeyMap || {}),
                    [versionFamily]: resolveSelectionKeys(keys, getVersionKeys(versionFamily)),
                  });
                }}
              >
                {getVersionKeys(versionFamily).map((versionKey) => (
                  <AccordionItem key={versionKey} aria-label={versionKey} startContent={versionKey} subtitle={titleMap[versionKey]}>
                    <CardPool historyList={cardGroup[versionFamily][versionKey]} />
                  </AccordionItem>
                ))}
              </Accordion>
            </AccordionItem>
          ))}
        </Accordion>
      </div>
    </DefaultLayout>
  );

  function getVersionFamilyKeys() {
    return Object.keys(cardGroup).sort(compareVersionFamilyDesc);
  }

  function getVersionKeys(versionFamily: string) {
    return Object.keys(cardGroup[versionFamily] || {}).sort(compareVersionDesc);
  }

  function getSelectedFamilyKeys() {
    if (Array.isArray(expandedFamilyKeys)) {
      return expandedFamilyKeys;
    }

    return getVersionFamilyKeys().slice(0, 1);
  }

  function getSelectedVersionKeys(versionFamily: string) {
    if (expandedVersionKeyMap?.[versionFamily]) {
      return expandedVersionKeyMap[versionFamily];
    }

    return getVersionKeys(versionFamily).slice(0, 1);
  }

  function getVersionFamilySubtitle(versionFamily: string) {
    const versionKeys = getVersionKeys(versionFamily);
    const poolCount = versionKeys.reduce((sum, versionKey) => sum + cardGroup[versionFamily][versionKey].length, 0);

    return `${versionKeys.length} 个版本 / ${poolCount} 个卡池`;
  }

  function resolveSelectionKeys(keys: any, allKeys: string[]) {
    return keys === 'all' ? allKeys : [...keys].map(String);
  }
}
