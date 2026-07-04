import { CardPool, getHistoryEndTime } from '@/components/card-pool';
import DefaultLayout from '@/layouts/default';
import { Accordion, AccordionItem } from '@heroui/react';
import { groupBy } from 'lodash';
import { useEffect, useState, useRef } from 'react';
import { useLocalStorage } from 'react-use';
import { useParams } from 'react-router-dom';

export default function HistoryPage() {
  const [cardGroup, setCardGroup] = useState<any>({});
  const [titleMap, setTitleMap] = useState<any>({});
  const [expandedKeys, setExpandedKeys] = useLocalStorage('history/expandedKeys', null); // 初始值为空
  const accordionExpandedKeys = expandedKeys ?? [];
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
          let versionGroup = groupBy(data, 'version');
          console.log('versionGroup:::', versionGroup);

          // 设置group
          setCardGroup(versionGroup);

          Object.keys(versionGroup).forEach((key) => {
            // 卡池图片没有的时候，使用角色立绘
            // console.log(`key::: ${key}`, versionGroup[key]);
            versionGroup[key].forEach((item) => {
              // console.log(`item::: ${item.s}`, item);
              console.log(`role::: ${key}`, role);
              const promotionImg = role?.[item['s']]?.['promotion_img'];
              const simpleImg = role?.[item['s']]?.['simple_img'];
              item['img'] = promotionImg?.[1] || promotionImg?.[0] || item['img_path'] || item['img'] || simpleImg;
            });

            // 没有图片的再排除
            versionGroup[key] = versionGroup[key].filter((item) => item.img !== '' && item.img);

            // 设置title
            setTitleMap((pre) => {
              const roleNames = versionGroup[key]
                .filter((item) => item.type === '角色')
                .flatMap((item) => (Array.isArray(item.s) ? item.s : [item.s]))
                .filter(Boolean);
              const fallbackNames = versionGroup[key]
                .flatMap((item) => (Array.isArray(item.s) ? item.s : [item.s || item.title]))
                .filter(Boolean);
              const displayNames = roleNames.length > 0 ? roleNames : fallbackNames;

              return {
                ...pre,
                [key]: `${versionGroup[key][0]?.timer ?? ''} ${displayNames.join('、')}`.trim(),
              };
            });
          });
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
          expandedKeys={accordionExpandedKeys}
          selectionMode="multiple"
          variant="splitted"
          onExpandedChange={(keys) => {
            setExpandedKeys([...keys]);
          }}
        >
          {Object.keys(cardGroup)
            .sort((a, b) => {
              const endDiff = getGroupEndTime(cardGroup[a]) - getGroupEndTime(cardGroup[b]);
              return endDiff || a.localeCompare(b);
            })
            .map((key) => (
              <AccordionItem key={key} aria-label={key} startContent={key} subtitle={titleMap[key]}>
                <CardPool historyList={cardGroup[key]} />
              </AccordionItem>
            ))}
        </Accordion>
      </div>
    </DefaultLayout>
  );

  function getGroupEndTime(historyList: any[]) {
    const endTimeList = historyList.map((item) => getHistoryEndTime(item.timer));
    return Math.min(...endTimeList);
  }
}
