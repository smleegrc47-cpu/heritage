import { Injectable, NotFoundException } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';

@Injectable()
export class AdminService {
  constructor(private prisma: PrismaService) {}

  async getAdminHeritages(status?: string, needsImprovement?: boolean) {
    const where: any = {};
    if (status) where.status = status;
    if (needsImprovement !== undefined) where.needsImprovement = needsImprovement;

    return this.prisma.heritage.findMany({
      where,
      orderBy: { createdAt: 'desc' },
      include: {
        images: true,
        reportedBy: { select: { id: true, name: true, email: true } },
      },
    });
  }

  async approveHeritage(id: string, reviewerNote?: string) {
    const heritage = await this.prisma.heritage.findUnique({ where: { id } });
    if (!heritage) {
      throw new NotFoundException('해당 제보 항목을 찾을 수 없습니다.');
    }

    return this.prisma.heritage.update({
      where: { id },
      data: {
        status: 'approved',
        reviewerNote: reviewerNote || heritage.reviewerNote,
      },
    });
  }

  async rejectHeritage(id: string, reviewerNote?: string) {
    const heritage = await this.prisma.heritage.findUnique({ where: { id } });
    if (!heritage) {
      throw new NotFoundException('해당 제보 항목을 찾을 수 없습니다.');
    }

    return this.prisma.heritage.update({
      where: { id },
      data: {
        status: 'rejected',
        reviewerNote: reviewerNote || heritage.reviewerNote,
      },
    });
  }

  async updateHeritage(
    id: string,
    dto: {
      name?: string;
      era?: string;
      dong?: string;
      description?: string;
      thinkingPoint?: string;
      reviewerNote?: string;
      needsImprovement?: boolean;
    },
  ) {
    const heritage = await this.prisma.heritage.findUnique({ where: { id } });
    if (!heritage) {
      throw new NotFoundException('해당 문화유산을 찾을 수 없습니다.');
    }

    return this.prisma.heritage.update({
      where: { id },
      data: { ...dto },
    });
  }

  async getReviewIssues() {
    return this.prisma.review.findMany({
      where: {
        OR: [
          { parkingNote: { not: null } },
          { restroomNote: { not: null } },
          { heritage: { needsImprovement: true } },
        ],
      },
      orderBy: { createdAt: 'desc' },
      include: {
        heritage: true,
        user: { select: { id: true, name: true, email: true } },
      },
    });
  }

  async getReportStats() {
    const [eraStats, dongStats, totalUsers, totalReviews, statusCount] = await Promise.all([
      this.prisma.heritage.groupBy({
        by: ['era'],
        _count: { id: true },
      }),
      this.prisma.heritage.groupBy({
        by: ['dong'],
        _count: { id: true },
      }),
      this.prisma.user.count(),
      this.prisma.review.count(),
      this.prisma.heritage.groupBy({
        by: ['status'],
        _count: { id: true },
      }),
    ]);

    return {
      eraStats: eraStats.map((e) => ({ era: e.era || '기타', count: e._count.id })),
      dongStats: dongStats.map((d) => ({ dong: d.dong || '전체', count: d._count.id })),
      statusCount: statusCount.map((s) => ({ status: s.status, count: s._count.id })),
      totalUsers,
      totalReviews,
      generatedAt: new Date(),
    };
  }

  async exportReport(format = 'pdf') {
    const stats = await this.getReportStats();
    return {
      format,
      downloadUrl: `https://storage.sejong.go.kr/reports/admin_report_${Date.now()}.${format}`,
      statsSummary: stats,
    };
  }
}
