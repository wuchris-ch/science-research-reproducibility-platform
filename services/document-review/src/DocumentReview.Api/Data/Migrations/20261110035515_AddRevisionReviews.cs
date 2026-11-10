using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace DocumentReview.Api.Data.Migrations
{
    /// <inheritdoc />
    public partial class AddRevisionReviews : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "RevisionReviews",
                columns: table => new
                {
                    Id = table.Column<Guid>(type: "uniqueidentifier", nullable: false),
                    RevisionId = table.Column<Guid>(type: "uniqueidentifier", nullable: false),
                    Reviewer = table.Column<string>(type: "nvarchar(200)", maxLength: 200, nullable: false),
                    Decision = table.Column<string>(type: "nvarchar(16)", maxLength: 16, nullable: false),
                    Comment = table.Column<string>(type: "nvarchar(2000)", maxLength: 2000, nullable: true),
                    ReviewedAt = table.Column<DateTimeOffset>(type: "datetimeoffset", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_RevisionReviews", x => x.Id);
                    table.ForeignKey(
                        name: "FK_RevisionReviews_DocumentRevisions_RevisionId",
                        column: x => x.RevisionId,
                        principalTable: "DocumentRevisions",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateIndex(
                name: "IX_RevisionReviews_RevisionId_Reviewer",
                table: "RevisionReviews",
                columns: new[] { "RevisionId", "Reviewer" },
                unique: true);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "RevisionReviews");
        }
    }
}
