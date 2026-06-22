import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { MemoryRouter } from 'react-router-dom';

import { BusinessPageShell } from './business-page-shell';

describe('BusinessPageShell', () => {
  it('shows the core business sections and skips empty optional regions', () => {
    render(
      <MemoryRouter>
        <BusinessPageShell
          title="研究中心"
          purpose="导入文章并整理规则提取结果。"
          inputDescription="需要一篇文章或一组文章。"
          processingDescription="系统会提取规则、整理证据并等待审核。"
          outputDescription="输出可审核的规则候选和处理说明。"
          prerequisites={[
            { label: '已完成导入', status: 'ready', detail: '文章已经进入待处理列表。' },
            { label: '补齐数据', status: 'unavailable', detail: '市场数据暂时缺失，稍后再处理。' },
          ]}
        />
      </MemoryRouter>,
    );

    expect(screen.getByRole('heading', { name: '研究中心' })).toBeInTheDocument();
    expect(screen.getByText('页面用途')).toBeInTheDocument();
    expect(screen.getByText('输入')).toBeInTheDocument();
    expect(screen.getByText('处理状态')).toBeInTheDocument();
    expect(screen.getByText('输出')).toBeInTheDocument();
    expect(screen.getByText('下一步')).toBeInTheDocument();
    expect(screen.queryByText('暂无内容')).not.toBeInTheDocument();
    expect(screen.queryByText('空状态')).not.toBeInTheDocument();
    expect(screen.getByText('已完成导入')).toBeInTheDocument();
    expect(screen.getByText('文章已经进入待处理列表。')).toBeInTheDocument();
    expect(screen.getByText('补齐数据')).toBeInTheDocument();
    expect(screen.getByText('市场数据暂时缺失，稍后再处理。')).toBeInTheDocument();
  });

  it('shows truthful default copy for non-ready states and hides the next action when permission is denied', () => {
    render(
      <MemoryRouter>
        <BusinessPageShell
          title="系统管理"
          purpose="查看系统状态并管理受控操作。"
          inputDescription="需要具备足够权限的账号。"
          processingDescription="系统会校验权限并准备页面内容。"
          outputDescription="输出可访问内容或明确的处理结果。"
          availability="permission_denied"
          nextAction={{ label: '发布数据库迁移', onClick: () => void 0 }}
        />
      </MemoryRouter>,
    );

    expect(screen.getAllByText('无权限')).not.toHaveLength(0);
    expect(screen.getByText('当前账号没有查看这部分内容的权限。')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '发布数据库迁移' })).not.toBeInTheDocument();
  });

  it('does not render empty content containers when optional regions are absent', () => {
    const { container } = render(
      <MemoryRouter>
        <BusinessPageShell
          title="空壳页面"
          purpose="检查空区域渲染。"
          inputDescription="输入说明。"
          processingDescription="处理说明。"
          outputDescription="输出说明。"
        />
      </MemoryRouter>,
    );

    expect(container.querySelector('[data-testid="section-content-页面用途"]')).not.toBeInTheDocument();
    expect(container.querySelector('[data-testid="section-content-输入"]')).not.toBeInTheDocument();
    expect(container.querySelector('[data-testid="section-content-输出"]')).not.toBeInTheDocument();
    expect(container.querySelector('[data-testid="section-content-下一步"]')).toBeInTheDocument();
    expect(screen.getByText('当前没有可执行的下一步操作。')).toBeInTheDocument();
  });

  it('renders a recovery action for error states', () => {
    render(
      <MemoryRouter>
        <BusinessPageShell
          title="数据管理"
          purpose="检查并修复缺失数据。"
          inputDescription="需要确认缺失范围。"
          processingDescription="系统正在检查缺失数据。"
          outputDescription="输出缺失范围和恢复建议。"
          availability="error"
          recoveryAction={{ label: '去补齐数据', to: '/system/data' }}
        />
      </MemoryRouter>,
    );

    expect(screen.getAllByText('出现问题').length).toBeGreaterThan(0);
    expect(screen.getByText('当前结果可能不完整或无法展示。')).toBeInTheDocument();
    expect(screen.getByText('去补齐数据')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '去补齐数据' })).toHaveAttribute('href', '/system/data');
  });

  it.each([
    ['loading', '正在加载', '页面内容正在获取中，请稍后再看。', '你暂时还不能查看完整内容。', '等待加载完成后刷新页面。'],
    ['empty', '暂无内容', '当前没有可展示的业务内容。', '这部分页面暂时不会给出结果。', '补齐输入后重新查看。'],
    ['error', '出现问题', '读取页面内容时发生了错误。', '当前结果可能不完整或无法展示。', '查看失败原因后重新处理。'],
    ['partial', '部分完成', '已返回一部分内容，仍有项目未处理完。', '你看到的是当前可用的部分结果。', '补齐缺失部分后继续处理。'],
    ['degraded', '已降级', '系统以受限方式返回结果，部分正式能力暂时不可用。', '当前结果只能作为受限参考，不能当成完整正式结果。', '先查看受限原因，再补齐缺失依赖或联系管理员处理。'],
    ['invalid', '状态无效', '当前正式数据或页面状态未通过有效性检查。', '继续操作可能导致错误判断，当前流程不能直接继续。', '先修复无效状态，再重新进入当前页面。'],
    ['conflict', '数据冲突', '页面依赖的正式数据之间出现冲突。', '当前结果无法作为唯一依据，相关业务步骤需要暂停。', '先确认冲突来源并完成修复，再继续后续操作。'],
    ['permission_denied', '无权限', '当前账号没有查看这部分内容的权限。', '高风险操作不会显示。', '切换到有权限的账号，或联系管理员。'],
    ['unavailable', '当前不可用', '相关服务或数据暂时不可用。', '暂时无法继续查看完整页面。', '稍后重试，或先补齐缺失数据。'],
  ] as const)('uses truthful default copy for %s', (availability, title, description, impact, recoveryAction) => {
    render(
      <MemoryRouter>
        <BusinessPageShell
          title="状态检查"
          purpose="检查当前业务状态。"
          inputDescription="需要当前请求信息。"
          processingDescription="系统会处理并返回状态。"
          outputDescription="输出状态和后续处理建议。"
          availability={availability}
        />
      </MemoryRouter>,
    );

    expect(screen.getAllByText(title).length).toBeGreaterThan(0);
    expect(screen.getAllByText(description).length).toBeGreaterThan(0);
    expect(screen.getByText('发生了什么')).toBeInTheDocument();
    expect(screen.getByText('影响什么：')).toBeInTheDocument();
    expect(screen.getByText(impact)).toBeInTheDocument();
    expect(screen.getByText('应该怎么处理：')).toBeInTheDocument();
    expect(screen.getByText(recoveryAction)).toBeInTheDocument();
  });
});
